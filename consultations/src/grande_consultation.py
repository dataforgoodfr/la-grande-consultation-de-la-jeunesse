#!/usr/bin/env python3
"""
Analysis of the "La grande Consultation" questionnaire results.

Usage:
    python src/grande_consultation.py file.xlsx [output_folder]

Writes into the output folder (default: ./resultats):
    - resultats.xlsx        : all the tables (one sheet per analysis)
    - donnees_propres.csv   : recoded data (scores, age brackets, etc.)

Dependencies: pandas, numpy, scikit-learn, openpyxl

Convention: code (functions, variables, comments) is in English; everything that ends up in a
report (sheet names, column headers, warnings, answer labels) stays in French.
"""

import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score

import geo
from common import order_by_list, split_outside_parentheses, wilson

# --------------------------------------------------------------------------
# SETTINGS (adjust here)
# --------------------------------------------------------------------------
MIN_N = 20  # below this size a group is flagged "effectif trop faible"
MIN_N_DEPT = 10  # display threshold for a département
K_RANGE = range(3, 6)  # numbers of profiles tried (3 to 5)

# Ordinal scales: label -> score. Unknown labels are reported.
LIKERT_AGREEMENT = {
    "Non, pas du tout": 1,
    "Non, pas vraiment": 2,
    "Oui, plutôt": 3,
    "Oui, tout à fait": 4,
}
LIKERT_IMPORTANCE = {
    "Pas du tout important": 1,
    "Peu important": 2,
    "Important": 3,
    "Très important": 4,
}
READING = {"Non": 1, "En partie": 2, "Oui, intégralement": 3}
NO_OPINION = {"Je ne sais pas", "Je préfère ne pas répondre"}  # never part of a score

# Question number -> scale used to turn the answer into a score
ORDINALS = {
    3: LIKERT_AGREEMENT,
    6: READING,
    4: LIKERT_AGREEMENT,
    7: LIKERT_AGREEMENT,
    8: LIKERT_AGREEMENT,
    9: LIKERT_IMPORTANCE,
    10: LIKERT_AGREEMENT,
    11: LIKERT_AGREEMENT,
    19: LIKERT_AGREEMENT,
}

# Profile variables (question number -> column name in the recoded data) used for the crossings
PROFILE = {
    24: "tranche_age",
    25: "genre",
    26: "niveau_etudes",
    27: "situation",
    14: "orientation_politique",
    "idf": "region_idf",
}

FREE_TEXT_Q = 13

# Age brackets created from Q24 (upper bounds: 17, 22, 120)
AGE_BRACKETS = ["15-17 ans (mineur·es)", "18-22 ans (primo votant·es)", "23-24 ans"]

# Display order of the categories (the others are appended after)
ORDERS = {
    "niveau_etudes": [
        "Aucun diplôme",
        "Brevet des collèges",
        "CAP, BEP ou diplôme de niveau équivalent",
        "Baccalauréat général, technologique, professionnel",
        "Bac+2 ou diplôme de niveau équivalent",
        "Bac+3 ou +4, ou diplôme de niveau équivalent",
        "Bac+5, ou diplôme de niveau équivalent",
        "Bac+8 et plus, doctorat",
    ],
    "situation": ["Collégien·ne", "Lycéen·ne", "Étudiant·e", "En emploi", "Sans emploi"],
    "orientation_politique": [
        "Extrême-gauche",
        "Gauche",
        "Centre-gauche",
        "Écologiste",
        "Centre",
        "Centre-droite",
        "Droite",
        "Extrême-droite",
    ],
    "tranche_age": AGE_BRACKETS,
}
# Multiple-choice questions exported as ONE text column (options separated by commas):
# they are exploded into one option per column.
TEXT_MULTIPLE_QS = {1, 2, 5}
RANKED_QS = {5}  # answer order matters (1st position = main choice)
AGE_Q = 24
DEPT_Q = 28
IDF = {"75", "77", "78", "91", "92", "93", "94", "95"}  # Île-de-France département codes
NO_ANSWER = "Je préfère ne pas répondre"

STOPWORDS = set(
    """le la les un une des de du d l et ou à a au aux en est être
je il elle on ce ca ça qui que qu pour par pas plus très trop mon ma mes son sa
ses sont avec sans sur dans se si ne y""".split()
)


# --------------------------------------------------------------------------
# LOADING AND STRUCTURE
# --------------------------------------------------------------------------
def load(path):
    """Read the Excel export and drop repeated Submission IDs (the same submission exported twice)."""
    df = pd.read_excel(path)
    if "Submission ID" in df.columns:
        n = len(df)
        df = df.drop_duplicates("Submission ID")
        if len(df) < n:
            print(f"  {n - len(df)} doublon(s) supprimé(s)")
    return df


def question_number(column):
    """Number of a question from its column header ("24. Quel âge ?").

    Tolerant to invisible characters (non-breaking space, BOM, leading spaces).
    Returns None when the header is not numbered.
    """
    h = unicodedata.normalize("NFKC", str(column))
    h = re.sub(r"[​‌‍⁠﻿]", "", h)
    m = re.match(r"^\s*(\d+)\s*[.)]\s*\S", h)
    return int(m.group(1)) if m else None


def discover_questions(df):
    """Group the columns by question number. Returns {n: dict}.

    Each dict has: text (header), type ("single" | "multiple" | "text"), column (single/text),
    text_column and options {label: boolean column} (multiple), cols (all the columns of the question).
    """
    questions = {}
    for col in df.columns:
        n = question_number(col)
        if n is None:
            continue
        q = questions.setdefault(n, {"cols": []})
        q["cols"].append(col)
    for n, q in questions.items():
        cols = q["cols"]
        q["text"] = min(cols, key=len)  # the header without the trailing "(option)"
        if len(cols) == 1:
            q["type"] = "text" if n == FREE_TEXT_Q else "single"
            q["column"] = cols[0]
        else:
            q["type"] = "multiple"
            q["text_column"] = q["text"]
            q["options"] = {}
            for c in cols:
                if c == q["text"]:
                    continue
                label = c[len(q["text"]) :].strip()
                label = label[1:-1] if label.startswith("(") and label.endswith(")") else label
                q["options"][label] = c
    return questions


def check_structure(qs, df=None):
    """Check that the indispensable questions were recognised; otherwise explain what to look at."""
    required = {AGE_Q, DEPT_Q} | {n for n in PROFILE if isinstance(n, int)}
    missing = sorted(n for n in required if n not in qs)
    if not missing:
        return
    msg = [
        f"Questions introuvables dans le fichier : {', '.join('Q' + str(n) for n in missing)}.",
        f"Questions reconnues ({len(qs)}) : {', '.join('Q' + str(n) for n in sorted(qs)) or 'aucune'}.",
        "Le script repère une question grâce au début de son en-tête de colonne, de la forme « 24. Quel âge avez-vous ? ».",
        "Vérifiez que le chemin pointe bien vers l'export de la Grande Consultation, et non vers un autre fichier.",
    ]
    if df is not None:
        others = [repr(str(c)) for c in df.columns if question_number(c) is None][:8]
        msg.append("Premières colonnes non reconnues (les caractères invisibles apparaissent) : " + " | ".join(others))
    raise ValueError("\n".join(msg))


def normalize_other(x):
    """ "Autre : blabla" -> "Autre" (free-text details are not categories)."""
    if isinstance(x, str):
        x = x.strip()
        if x.lower().startswith("autre"):
            return "Autre"
    return x


def clean_text(s):
    """Strip a text column and group the "Autre : …" answers; returns a pandas string Series."""
    return s.astype("string").str.strip().map(normalize_other).astype("string")


def split_choices(value):
    """Split a multi-choice cell on the commas outside parentheses, grouping the "Autre : …" answers."""
    return split_outside_parentheses(value, clean=normalize_other)


# Options whose label contains a comma OUTSIDE parentheses: they must be protected when a multiple-choice
# question is exported as one text column (otherwise "Signer, lancer…" would be cut into two fake choices).
COMMA_OPTIONS = ["Participer à des ateliers, débats", "Signer, lancer ou relayer des pétitions"]


def split_protected(value):
    """Like `split_choices`, but keeps the commas that belong to the labels listed in COMMA_OPTIONS."""
    if isinstance(value, str):
        for o in COMMA_OPTIONS:
            value = value.replace(o, o.replace(",", "⁣"))  # temporary invisible separator
    return [x.replace("⁣", ",") for x in split_choices(value)]


def explode_text_answers(df, qs):
    """Create one boolean column per option for the multiple-choice questions exported as plain text.

    Concerned: the questions in TEXT_MULTIPLE_QS and every single-column question whose title says
    "(N choix maximum)" (the Tally export varies between versions). Modifies `df` and `qs` in place.
    """
    announced = {n for n, q in qs.items() if q["type"] == "single" and re.search(r"choix maximum", q["text"], re.I)}
    for n in sorted(TEXT_MULTIPLE_QS | announced):
        if n not in qs or qs[n]["type"] != "single":
            continue
        col = qs[n]["column"]
        lists = df[col].map(split_protected)
        # The commas inside an "Autre : texte, texte" create fake choices:
        # keep only the options seen in answers that do not contain "Autre".
        known = {x for items in lists if "Autre" not in items for x in items}
        if known:
            lists = lists.map(lambda items: [x for x in items if x == "Autre" or x in known])
        labels = sorted({x for items in lists for x in items})
        qs[n]["type"] = "multiple"
        qs[n]["text_column"] = col
        qs[n]["options"] = {}
        for lab in labels:
            name = f"{col} [{lab}]"
            df[name] = lists.map(lambda items, lab=lab: lab in items)
            qs[n]["options"][lab] = name
        qs[n]["lists"] = lists


def export_boolean_columns(path, output):
    """Write a copy of the export with one true/false column per option of each exploded question.

    The columns are named "question (option)" as in a full Tally export. The original text column is kept
    (it carries the answer order, useful for Q5). The file can be read back with `load`:
    the script then has nothing left to split. Returns (number of new columns, output path).
    """
    df = load(path)
    qs = discover_questions(df)
    before = set(df.columns)
    explode_text_answers(df, qs)
    new_cols = [c for c in df.columns if c not in before]
    renaming, after = {}, {}
    for q in qs.values():
        if "lists" not in q:
            continue
        for lab, name in q["options"].items():
            renaming[name] = f"{q['text_column']} ({lab})"
            after.setdefault(q["text_column"], []).append(renaming[name])
    df = df.rename(columns=renaming)
    # the created columns go right after their text column
    order = []
    for c in df.columns:
        if c in renaming.values():
            continue
        order.append(c)
        order.extend(after.get(c, []))
    df = df[order]
    df.to_excel(output, index=False)
    return len(new_cols), output


def cross(d, row, column, mask=None, row_order=None, column_order=None, sort_by=None, n_min=None):
    """Cross two variables of `d`. Returns (long table, summary).

    Long table columns: row, category, n, base (size of the row), pct (share within the row).
    Rows with fewer than `n_min` respondents (MIN_N by default) are dropped and listed in the summary.
    `mask`: booleans restricting the base (e.g. people old enough to vote).
    `sort_by`: category of `column` used to rank the rows (descending).
    Summary keys: n (respondents kept), dropped (list of dropped rows).
    """
    n_min = MIN_N if n_min is None else n_min
    sub = d if mask is None else d[mask]
    sub = sub[[row, column]].dropna()
    sub = sub[(sub[row] != NO_ANSWER) & (sub[column] != NO_ANSWER)].astype(str)
    tab = pd.crosstab(sub[row], sub[column])
    dropped = tab.index[tab.sum(axis=1) < n_min].tolist()
    tab = tab.drop(index=dropped)
    if tab.empty:
        raise ValueError(
            f"Croisement {row} × {column} impossible : aucune ligne n'a au moins {n_min} répondant·es "
            f"(base : {len(sub)}). Vérifiez les libellés des modalités et le filtre utilisé."
        )
    if row_order:
        tab = tab.reindex(order_by_list(list(tab.index), row_order))
    elif sort_by in tab.columns:
        tab = tab.loc[(tab[sort_by] / tab.sum(axis=1)).sort_values(ascending=False).index]
    tab = tab[order_by_list(list(tab.columns), column_order)] if column_order else tab
    long = tab.stack().rename("n").reset_index()
    long.columns = ["row", "category", "n"]
    long["base"] = long.groupby("row")["n"].transform("sum")
    long["pct"] = long["n"] / long["base"]
    return long, {"n": int(tab.values.sum()), "dropped": dropped}


def stats_note(r):
    """Short sentence for a chart subtitle (`r` = summary from `cross`): names the dropped (too small) groups."""
    if not r["dropped"]:
        return ""
    return f"écartés (< {MIN_N}) : " + ", ".join(map(str, r["dropped"]))


def options_by_profile(df, d, qs, n, profile, group_order=None):
    """Multiple-choice question x profile variable: share of each group that ticked each option.

    Returns (long table with the Wilson CI of each share, dropped groups).
    """
    q = qs[n]
    groups = d[profile].dropna().astype(str)
    groups = groups[groups != NO_ANSWER]
    sizes = groups.value_counts()
    dropped = sizes[sizes < MIN_N].index.tolist()
    kept = [g for g in (group_order or list(sizes.index)) if g in sizes.index and g not in dropped]
    rows = []
    for label, col in q["options"].items():
        ticked = as_bool(df[col])
        for grp in kept:
            idx = groups.index[groups == grp]
            k = int(ticked.loc[idx].sum())
            lo, hi = wilson(k, len(idx))
            rows.append(
                {
                    "option": label,
                    "groupe": grp,
                    "effectif": k,
                    "n groupe": len(idx),
                    "pct": k / len(idx),
                    "IC95 bas": lo,
                    "IC95 haut": hi,
                }
            )
    long = pd.DataFrame(rows)
    if long.empty:
        raise ValueError(f"Q{n} × {profile} : aucun groupe n'a au moins {MIN_N} répondant·es.")
    return long, dropped


def compare_options(df, qs, n, mask_a, mask_b, name_a, name_b):
    """Multiple-choice question: share of groups A and B that ticked each option, and the gap in points.

    The masks are booleans aligned on `df`. One row per option, largest gap (in absolute value) first.
    """
    rows = []
    na, nb = int(mask_a.sum()), int(mask_b.sum())
    for label, col in qs[n]["options"].items():
        ticked = as_bool(df[col])
        ka, kb = int(ticked[mask_a].sum()), int(ticked[mask_b].sum())
        pa, pb = (ka / na if na else np.nan), (kb / nb if nb else np.nan)
        rows.append(
            {
                "option": label,
                name_a: pa,
                name_b: pb,
                "n A": na,
                "n B": nb,
                "écart B − A (points)": (pb - pa) * 100,
            }
        )
    out = pd.DataFrame(rows)
    order = out["écart B − A (points)"].abs().sort_values(ascending=False).index
    return out.loc[order].reset_index(drop=True)


def ranking_table(qs):
    """For the ranked questions (RANKED_QS): % in 1st position and average rank of each option."""
    rows = []
    for n in RANKED_QS:
        if n not in qs or "lists" not in qs[n]:
            continue
        lists = qs[n]["lists"]
        base = int((lists.map(len) > 0).sum())
        for lab in qs[n]["options"]:
            ranks = [items.index(lab) + 1 for items in lists if lab in items]
            first = sum(1 for items in lists if items and items[0] == lab)
            lo, hi = wilson(first, base)
            rows.append(
                {
                    "question": n,
                    "option": lab,
                    "% en 1re position": first / base,
                    "IC95 bas": lo,
                    "IC95 haut": hi,
                    "rang moyen": np.mean(ranks) if ranks else np.nan,
                    "base": base,
                }
            )
    return pd.DataFrame(rows)


def as_bool(s):
    """Turn a column of "True"/"False" (text or boolean) into real booleans."""
    return s.astype(str).str.strip().str.lower().eq("true")


# --------------------------------------------------------------------------
# RECODING
# --------------------------------------------------------------------------
def recode(df, qs):
    """Build the clean analysis table `d` (one row per respondent) from the raw export.

    Adds: scores for the ordinal questions (Q{n}_score), age and age bracket, profile variables,
    Île-de-France flag and cleaned copies of the single-choice answers.
    Returns (d, labels not recognised per question).
    """
    d = pd.DataFrame({"submission_id": df["Submission ID"]}) if "Submission ID" in df else pd.DataFrame(index=df.index)
    unmapped = {}

    # Ordinal scores
    for n, mapping in ORDINALS.items():
        if n not in qs:
            continue
        s = df[qs[n]["column"]].astype("string").str.strip()
        d[f"Q{n}_score"] = s.map(mapping).astype(float)
        unknown = sorted(set(s.dropna()) - set(mapping) - NO_OPINION)
        if unknown:
            unmapped[n] = unknown

    # Profile
    age = pd.to_numeric(df[qs[AGE_Q]["column"]], errors="coerce")
    d["age"] = age
    d["tranche_age"] = pd.cut(age, [0, 17, 22, 120], labels=AGE_BRACKETS)
    for n, name in PROFILE.items():
        if n in ("idf", 24):
            continue
        d[name] = clean_text(df[qs[n]["column"]])

    dept = df[qs[DEPT_Q]["column"]].astype("string")
    d["departement"] = dept
    code = dept.str.extract(r"^\s*(\w+)\s*-")[0]
    d["region_idf"] = np.where(code.isna(), pd.NA, np.where(code.isin(IDF), "Île-de-France", "Hors Île-de-France"))

    # Non-ordinal single-choice questions (raw copy for the crossings)
    for n, q in qs.items():
        if q["type"] == "single" and f"Q{n}_score" not in d and n not in PROFILE:
            d[f"Q{n}"] = clean_text(df[q["column"]])
    for n in ORDINALS:
        if n in qs:
            d[f"Q{n}"] = clean_text(df[qs[n]["column"]])

    return d, unmapped


# --------------------------------------------------------------------------
# ANALYSES
# --------------------------------------------------------------------------
def frequency_tables(df, d, qs):
    """One-way tables of every single-choice question: count, %, Wilson CI and non-response."""
    rows = []
    for n, q in sorted(qs.items()):
        if q["type"] != "single":
            continue
        s = d[f"Q{n}"] if f"Q{n}" in d else df[q["column"]].astype("string")
        if n in PROFILE:
            s = d[PROFILE[n]] if n != AGE_Q else d["tranche_age"].astype("string")
        base = s.notna().sum()
        for val, k in s.value_counts().items():
            lo, hi = wilson(k, base)
            rows.append(
                {
                    "question": n,
                    "intitulé": q["text"],
                    "réponse": val,
                    "effectif": k,
                    "base": base,
                    "%": k / base,
                    "IC95 bas": lo,
                    "IC95 haut": hi,
                    "non-réponse (%)": 1 - base / len(s),
                }
            )
    return pd.DataFrame(rows)


def multiple_choice_tables(df, qs):
    """Counts and % of respondents for every option of every multiple-choice question."""
    rows = []
    for n, q in sorted(qs.items()):
        if q["type"] != "multiple":
            continue
        base = len(df)
        for label, col in q["options"].items():
            k = int(as_bool(df[col]).sum())
            lo, hi = wilson(k, base)
            rows.append(
                {
                    "question": n,
                    "intitulé": q["text"],
                    "option": label,
                    "effectif": k,
                    "base": base,
                    "% des répondants": k / base,
                    "IC95 bas": lo,
                    "IC95 haut": hi,
                }
            )
    out = pd.DataFrame(rows)
    return out.sort_values(["question", "effectif"], ascending=[True, False])


def simple_crossings(d, qs):
    """Every single-choice question x every profile variable: distribution of the answers within each group."""
    detail = []
    targets = [
        f"Q{n}"
        for n, q in sorted(qs.items())
        if q["type"] == "single" and n not in PROFILE and n != DEPT_Q and f"Q{n}" in d
    ]
    for target in targets:
        for name in PROFILE.values():
            sub = d[[target, name]].dropna()
            sub = sub[(sub[target] != NO_ANSWER) & (sub[name] != NO_ANSWER)]
            if sub.empty:
                continue
            tab = pd.crosstab(sub[name], sub[target])
            tab = tab.reindex(order_by_list(list(tab.index), ORDERS.get(name)))
            n_q = int(target[1:])
            answer_order = (
                sorted(ORDINALS[n_q], key=ORDINALS[n_q].get) + ["Je ne sais pas"] if n_q in ORDINALS else None
            )
            tab = tab[order_by_list(list(tab.columns), answer_order)]
            pct = tab.div(tab.sum(axis=1), axis=0)
            for grp in tab.index:
                for ans in tab.columns:
                    detail.append(
                        {
                            "question": target,
                            "variable_profil": name,
                            "groupe": grp,
                            "réponse": ans,
                            "effectif": tab.loc[grp, ans],
                            "n groupe": tab.loc[grp].sum(),
                            "% du groupe": pct.loc[grp, ans],
                            "effectif trop faible": tab.loc[grp].sum() < MIN_N,
                        }
                    )
    return pd.DataFrame(detail)


def multiple_crossings(df, d, qs):
    """Every option of every multiple-choice question x every profile group: count and % of the group."""
    rows = []
    for n, q in sorted(qs.items()):
        if q["type"] != "multiple":
            continue
        for name in PROFILE.values():
            groups = d[name]
            for grp, idx in groups.dropna().groupby(groups.dropna()).groups.items():
                if grp == NO_ANSWER:
                    continue
                for label, col in q["options"].items():
                    k = int(as_bool(df.loc[idx, col]).sum())
                    rows.append(
                        {
                            "question": n,
                            "variable_profil": name,
                            "groupe": grp,
                            "option": label,
                            "effectif": k,
                            "n groupe": len(idx),
                            "% du groupe": k / len(idx),
                            "effectif trop faible": len(idx) < MIN_N,
                        }
                    )
    return pd.DataFrame(rows)


def near_vs_urgent_causes(df, qs):
    """Q1 (cause close to me) vs Q2 (urgent cause), per cause, with the gap in points."""
    if 1 not in qs or 2 not in qs:
        return pd.DataFrame()
    q1, q2 = qs[1]["options"], qs[2]["options"]
    out = []
    for label in sorted(set(q1) | set(q2)):
        p1 = as_bool(df[q1[label]]).mean() if label in q1 else np.nan
        p2 = as_bool(df[q2[label]]).mean() if label in q2 else np.nan
        out.append(
            {
                "cause": label,
                "% proche (Q1)": p1,
                "% urgente (Q2)": p2,
                "écart urgente - proche (points)": (p2 - p1) * 100,
            }
        )
    return pd.DataFrame(out).sort_values("% urgente (Q2)", ascending=False)


def voting_analysis(d):
    """Q23 (intention to vote) among the people old enough to vote (Q22 == "Oui")."""
    if "Q23" not in d or "Q22" not in d:
        return pd.DataFrame()
    sub = d[d["Q22"] == "Oui"]
    out = []
    base = sub["Q23"].dropna()
    for val, k in base.value_counts().items():
        lo, hi = wilson(k, len(base))
        out.append(
            {
                "réponse Q23": val,
                "effectif": k,
                "base (en âge de voter)": len(base),
                "%": k / len(base),
                "IC95 bas": lo,
                "IC95 haut": hi,
            }
        )
    return pd.DataFrame(out)


def typical_profiles(d):
    """Cluster the respondents on their scores (Ward + silhouette to pick k). Returns (means, quality, columns)."""
    cols = [c for c in d.columns if c.endswith("_score")]
    X = d[cols].dropna()
    if len(X) < 30:
        return pd.DataFrame(), pd.DataFrame(), None
    Z = (X - X.mean()) / X.std(ddof=0).replace(0, 1)  # standardise each score
    best = None
    for k in K_RANGE:
        labels = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Z)
        sil = silhouette_score(Z, labels)
        if best is None or sil > best[0]:
            best = (sil, k, labels)
    sil, k, labels = best
    d.loc[X.index, "profil"] = [f"Profil {i + 1}" for i in labels]
    means = X.assign(profil=d.loc[X.index, "profil"]).groupby("profil").mean()
    means.insert(0, "effectif", d.loc[X.index].groupby("profil").size())
    means.insert(1, "% de l'échantillon", means["effectif"] / len(X))
    info = pd.DataFrame(
        [
            {
                "k retenu": k,
                "silhouette": sil,
                "lecture": "structure nette"
                if sil > 0.5
                else "structure faible : les profils sont indicatifs"
                if sil < 0.25
                else "structure moyenne",
                "variables": ", ".join(cols),
            }
        ]
    )
    return means.reset_index(), info, cols


def departments(d):
    """Number of respondents per département, with a flag for those above the display threshold."""
    s = d["departement"].dropna()
    t = s.value_counts().rename_axis("département").reset_index(name="effectif")
    t["affichable (≥ seuil)"] = t["effectif"] >= MIN_N_DEPT
    return t


def regions(d):
    """Number of respondents per région (from the département code of Q28), with a display flag.

    The départements are first counted by code (see `geo.count_by_department`), then summed per région.
    A région below MIN_N respondents is flagged as not displayable.
    """
    by_dept = geo.count_by_department(d["departement"])
    by_region = geo.count_by_region(by_dept)
    names = geo.names("region")
    t = pd.DataFrame(
        {"code région": by_region.index, "région": by_region.index.map(names), "effectif": by_region.values}
    )
    t["affichable (≥ seuil)"] = t["effectif"] >= MIN_N
    return t.sort_values("effectif", ascending=False).reset_index(drop=True)


def normalize_word(word):
    """Lower-case a word, remove its accents and surrounding punctuation."""
    word = unicodedata.normalize("NFKD", word.lower())
    return "".join(c for c in word if not unicodedata.combining(c)).strip(" .,;:!?'\"()-")


def free_text_words(df, qs):
    """Most frequent normalised answers and most frequent words of the free-text question (top 100 each)."""
    if FREE_TEXT_Q not in qs:
        return pd.DataFrame(), pd.DataFrame()
    s = df[qs[FREE_TEXT_Q]["column"]].dropna().astype(str)
    answers = Counter(normalize_word(x) for x in s if normalize_word(x))
    words = Counter()
    for x in s:
        for w in re.split(r"[\s,;/]+", x):
            w = normalize_word(w)
            if len(w) > 2 and w not in STOPWORDS:
                words[w] += 1
    return (
        pd.DataFrame(answers.most_common(100), columns=["réponse (normalisée)", "occurrences"]),
        pd.DataFrame(words.most_common(100), columns=["mot", "occurrences"]),
    )


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("resultats")
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load(path)
    qs = discover_questions(df)
    check_structure(qs, df)
    explode_text_answers(df, qs)
    print(f"{len(df)} répondants, {len(qs)} questions")
    if len(df) < 100:
        print(f"  ⚠ échantillon réduit ({len(df)}) : résultats indicatifs seulement")

    d, unmapped = recode(df, qs)
    for n, vals in unmapped.items():
        print(f"  ⚠ Q{n} : libellés non reconnus pour le score : {vals}")

    sheets = {
        "Tris à plat": frequency_tables(df, d, qs),
        "Choix multiples": multiple_choice_tables(df, qs),
        "Q5 classement": ranking_table(qs),
        "Causes proche vs urgente": near_vs_urgent_causes(df, qs),
    }
    sheets["Croisements"] = simple_crossings(d, qs)
    sheets["Multiples x profil"] = multiple_crossings(df, d, qs)
    sheets["Intention de vote (Q23)"] = voting_analysis(d)
    profiles_table, quality, _ = typical_profiles(d)
    sheets["Profils types"] = profiles_table
    sheets["Profils - qualité"] = quality
    sheets["Départements"] = departments(d)
    sheets["Régions"] = regions(d)
    answers, words = free_text_words(df, qs)
    sheets["Q13 réponses"] = answers
    sheets["Q13 mots"] = words
    sheets["Données manquantes"] = (
        df.isna().mean().rename("part de NaN").reset_index().rename(columns={"index": "colonne"})
    )

    with pd.ExcelWriter(out_dir / "resultats.xlsx") as xl:
        for name, t in sheets.items():
            if t is not None and not t.empty:
                t.to_excel(xl, sheet_name=name[:31], index=False)  # Excel limits sheet names to 31 characters
    d.to_csv(out_dir / "donnees_propres.csv", index=False)

    print(f"\nRésultats écrits dans {out_dir}/")

if __name__ == "__main__":
    main()
