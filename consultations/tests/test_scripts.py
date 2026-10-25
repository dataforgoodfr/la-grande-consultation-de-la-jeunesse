"""Run each script on SIMULATED data and check the outputs and a few invariants."""

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run_script(*args):
    r = subprocess.run([PY, *map(str, args)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout


@pytest.fixture(scope="module")
def gc(tmp_path_factory):
    d = tmp_path_factory.mktemp("gc")
    run_script("tests/gen_gc.py", d / "rep.xlsx", 600)
    sortie = run_script("src/grande_consultation.py", d / "rep.xlsx", d / "res")
    return d, sortie


def test_gc_produces_the_expected_sheets(gc):
    feuilles = pd.ExcelFile(gc[0] / "res" / "resultats.xlsx").sheet_names
    for attendu in ("Tris à plat", "Choix multiples", "Croisements", "Profils types", "Régions"):
        assert attendu in feuilles
    assert not {"Score composite", "Croisements - tests"} & set(feuilles)


def test_gc_removes_the_duplicate(gc):
    assert "1 doublon(s) supprimé(s)" in gc[1] and "599 répondants" in gc[1]


def test_gc_q1_is_exploded_into_options(gc):
    m = pd.read_excel(gc[0] / "res" / "resultats.xlsx", "Choix multiples")
    options = set(m[m.question == 1]["option"])
    assert "Autre" in options and not any(o.startswith("Autre :") for o in options)


def test_check_structure_clear_message():
    import pandas as pd

    import grande_consultation as g

    df = pd.DataFrame({"Quel âge avez-vous ?": [16], "1. Parmi ces causes": ["x"]})
    qs = g.discover_questions(df)
    with pytest.raises(ValueError, match="Questions introuvables"):
        g.check_structure(qs, df)


@pytest.mark.parametrize(
    "header",
    [
        "24. Quel âge avez-vous ?",
        " 24. Quel âge avez-vous ?",
        "\ufeff24. Quel âge avez-vous ?",
        "24.\u00a0Quel âge avez-vous ?",
        "\u200b24. Quel âge avez-vous ?",
        "24 . Quel âge avez-vous ?",
    ],
)
def test_question_number_tolerant(header):
    import grande_consultation as g

    assert g.question_number(header) == 24


def test_question_number_unnumbered():
    import grande_consultation as g

    assert g.question_number("Submission ID") is None
    assert g.question_number("Quel âge avez-vous ?") is None


def test_split_protected_comma_options():
    import grande_consultation as g

    v = "Voter, Signer, lancer ou relayer des pétitions, Participer à des ateliers, débats"
    assert g.split_protected(v) == [
        "Voter",
        "Signer, lancer ou relayer des pétitions",
        "Participer à des ateliers, débats",
    ]


def _crossing_sample():
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    n = 200
    d = pd.DataFrame(
        {
            "Q19": rng.choice(["Non", "Oui"], n),
            "Q23": rng.choice(["Non", "Oui", "Je ne sais pas"], n),
            "tranche_age": rng.choice(["15-17 ans (mineurs)", "18-20 ans"], n),
        }
    )
    df = pd.DataFrame({"opt": rng.random(n) < 0.3})
    qs = {1: {"options": {"A": "opt"}}}
    return d, df, qs


def test_cross_and_note():
    import grande_consultation as g

    d, _, _ = _crossing_sample()
    long, r = g.cross(d, "Q19", "Q23", column_order=["Non", "Oui", "Je ne sais pas"])
    assert set(long.columns) == {"row", "category", "n", "base", "pct"}
    assert abs(long.groupby("row")["pct"].sum() - 1).max() < 1e-9
    assert set(r) == {"n", "dropped"} and r["n"] == 200 and g.stats_note(r) == ""
    # rows under the threshold are dropped and reported
    petit = int(d["Q19"].value_counts().min())
    _, r2 = g.cross(d, "Q19", "Q23", n_min=petit + 1)
    assert len(r2["dropped"]) == 1 and "écartés" in g.stats_note(r2)


def test_cross_empty_raises_a_clear_error():
    import pytest

    import grande_consultation as g

    d, _, _ = _crossing_sample()
    with pytest.raises(ValueError, match="aucune ligne"):
        g.cross(d, "Q19", "Q23", n_min=10_000)


def test_compare_options_and_options_by_profile():
    import grande_consultation as g

    d, df, qs = _crossing_sample()
    a, b = d["Q23"] == "Non", d["Q23"] == "Oui"
    r = g.compare_options(df, qs, 1, a, b, "A", "B")
    assert {"A", "B", "écart B − A (points)"} <= set(r.columns) and len(r) == 1
    t, dropped = g.options_by_profile(df, d, qs, 1, "tranche_age")
    assert {"pct", "IC95 bas", "IC95 haut"} <= set(t.columns) and not dropped


def test_age_brackets_from_recode():
    """18-22 = first-time voters; 23 belongs to the last bracket. ORDERS uses the same labels."""
    import grande_consultation as g

    ages = [15, 17, 18, 22, 23, 24]
    df = pd.DataFrame(
        {
            "24. Quel âge avez-vous ?": ages,
            "25. Genre": ["Femme"] * 6,
            "26. Niveau d'études": ["Brevet des collèges"] * 6,
            "27. Situation": ["Lycéen·ne"] * 6,
            "14. Orientation": ["Centre"] * 6,
            "28. Département": ["75 - Paris"] * 6,
        }
    )
    d, unmapped = g.recode(df, g.discover_questions(df))
    assert d["tranche_age"].astype(str).tolist() == [g.AGE_BRACKETS[i] for i in (0, 0, 1, 1, 2, 2)]
    assert g.ORDERS["tranche_age"] == g.AGE_BRACKETS and not unmapped
