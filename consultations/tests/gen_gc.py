"""Generate SIMULATED answers to the Grande Consultation (no real data).

Column headers come from fixtures/gc_headers.json; values are drawn at random.
Usage: python gen_gc.py output.xlsx [n]
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

N = int(sys.argv[2]) if len(sys.argv) > 2 else 600
rng = np.random.default_rng(7)
H = json.load(open(Path(__file__).parent / "fixtures" / "gc_headers.json", encoding="utf-8"))

LIK = ["Non, pas du tout", "Non, pas vraiment", "Oui, plutôt", "Oui, tout à fait"]
CAUSES = [
    "Droits des animaux",
    "Droits des femmes",
    "Droits des personnes LGBTQIA+",
    "Droits humains",
    "Économie",
    "Éducation (orientation, égalité des chances)",
    "Emploi",
    "Handicap et lutte contre le validisme",
    "Harcèlement scolaire",
    "Justice climatique et protection de l’environnement (biodiversité, réduction des déchets)",
    "Justice sociale",
    "Logement",
    "Santé mentale (stress, anxiété, dépression)",
    "Sécurité",
    "Autre : le sport",
]
ACTEURS = ["Les responsables politiques", "Les associations", "Les citoyen·nes"]
POOLS = {
    3: LIK + ["Je ne sais pas"],
    4: LIK + ["Je ne sais pas"],
    6: ["Non", "En partie", "Oui, intégralement"],
    7: LIK,
    8: LIK + ["Je ne sais pas"],
    9: ["Pas du tout important", "Peu important", "Important", "Très important"],
    10: LIK,
    11: LIK,
    12: [
        "Ses propositions concrètes",
        "Sa personnalité, son charisme",
        "Son expérience",
        "Son appartenance politique, son parti",
    ],
    14: [
        "Centre",
        "Centre-gauche",
        "Centre-droite",
        "Droite",
        "Ecologiste",
        "Extrême-droite",
        "Extrême-gauche",
        "Gauche",
        "Je préfère ne pas répondre",
        "Autre : libertaire",
    ],
    15: [
        "Aux médias traditionnels (télévision, radio, journaux, magazines et affichage)",
        "Aux réseaux sociaux",
        "Aux sites internet",
    ],
    17: ["Non", "Oui"],
    19: LIK + ["Je ne sais pas"],
    22: ["Oui", "Non"],
    25: ["Femme", "Homme", "Non binaire", "Je préfère ne pas répondre", "Autre : agenre"],
    26: [
        "Aucun diplôme",
        "Brevet des collèges",
        "CAP, BEP ou diplôme de niveau équivalent",
        "Baccalauréat général, technologique, professionnel",
        "Bac+2 ou diplôme de niveau équivalent",
        "Bac+3 ou +4, ou diplôme de niveau équivalent",
        "Bac+5, ou diplôme de niveau équivalent",
        "Je préfère ne pas répondre",
    ],
    27: ["Collégien·ne", "Lycéen·ne", "Étudiant·e", "En emploi", "Sans emploi", "Je préfère ne pas répondre"],
    28: [
        "75 - Paris",
        "69 - Rhône",
        "13 - Bouches-du-Rhône",
        "33 - Gironde",
        "59 - Nord",
        "58 - Nièvre",
        "94 - Val-de-Marne",
    ],
}
MOTS = ["écoute", "honnête", "engagé", "proche", "juste", "courageux", "intègre", "réel"]


def num(h):
    m = re.match(r"^(\d+)\.\s", h)
    return int(m.group(1)) if m else None


def choisir_k(opts, kmax):
    k = int(rng.integers(1, kmax + 1))
    return list(rng.choice(opts, size=min(k, len(opts)), replace=False))


d = pd.DataFrame(
    {
        "Submission ID": [f"s{i:05d}" for i in range(N)],
        "Respondent ID": [f"r{i:05d}" for i in range(N)],
        "Submitted at": pd.Timestamp("2026-06-08") + pd.to_timedelta(rng.integers(0, 30 * 24 * 60, N), unit="m"),
    }
)
age = rng.integers(15, 25, N)
for h in H[3:]:
    n = num(h)
    if n in (1, 2) and h not in d:
        kmax = 3 if n == 1 else 2
        d[h] = [", ".join(choisir_k(CAUSES, kmax)) for _ in range(N)]
    elif n == 5:
        d[h] = [", ".join(rng.permutation(ACTEURS)) for _ in range(N)]
    elif n == 13:
        d[h] = [MOTS[i] if rng.random() < 0.8 else None for i in rng.integers(0, len(MOTS), N)]
    elif n == 23:
        d[h] = None  # rempli après Q22
    elif n == 24:
        d[h] = age
    elif n in POOLS and h not in d:
        d[h] = rng.choice(POOLS[n], size=N)
# questions à choix multiples avec colonnes vrai/faux : texte + une colonne par option
groupes = {}
for h in H[3:]:
    n = num(h)
    if n in (16, 18, 20, 21):
        groupes.setdefault(n, []).append(h)
for n, cols in groupes.items():
    base = min(cols, key=len)
    options = [c[len(base) :].strip()[1:-1] for c in cols if c != base]
    sel = [choisir_k(options, 2) for _ in range(N)]
    d[base] = [", ".join(s) for s in sel]
    for c, o in zip([c for c in cols if c != base], options):
        d[c] = [o in s for s in sel]
# Q23 : seulement si Q22 = Oui, avec quelques sauts non respectés
q22 = next(h for h in H if num(h) == 22)
q23 = next(h for h in H if num(h) == 23)
v = rng.choice(["Oui", "Non", "Je ne sais pas"], size=N, p=[0.6, 0.15, 0.25]).astype(object)
v[(d[q22] == "Non").to_numpy() & (rng.random(N) > 0.1)] = None
d[q23] = v
d = d[H]
d.loc[3, "Submission ID"] = d.loc[2, "Submission ID"]  # un doublon volontaire
d.to_excel(sys.argv[1], index=False)
print(d.shape)
