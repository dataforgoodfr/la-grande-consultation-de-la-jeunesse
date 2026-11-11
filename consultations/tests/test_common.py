import numpy as np
import pytest

from common import normalize, order_by_keywords, order_by_list, split_outside_parentheses, wilson


def test_wilson_central_proportion():
    low, high = wilson(50, 100)
    assert low == pytest.approx(0.4038, abs=1e-3)
    assert high == pytest.approx(0.5962, abs=1e-3)


def test_wilson_bounds_and_empty_base():
    low, high = wilson(0, 20)
    assert low == 0 and 0 < high < 0.2
    assert all(np.isnan(x) for x in wilson(0, 0))


def test_split_ignores_commas_inside_parentheses():
    texte = "Droits humains, Justice climatique (biodiversité, déchets), Autre : le sport"
    assert split_outside_parentheses(texte) == [
        "Droits humains",
        "Justice climatique (biodiversité, déchets)",
        "Autre : le sport",
    ]
    assert split_outside_parentheses(texte, clean=lambda x: "Autre" if x.startswith("Autre") else x)[-1] == "Autre"
    assert split_outside_parentheses(None) == []


def test_normalize_accents_and_apostrophes():
    assert normalize("  Énormément   d’IA ") == "enormement d'ia"


def test_ordering_helpers():
    assert order_by_list(["b", "z", "a"], ["a", "b"]) == ["a", "b", "z"]
    assert order_by_keywords(["Beaucoup", "Pas du tout", "Un peu"], ["pas du tout", "un peu", "beaucoup"]) == [
        "Pas du tout",
        "Un peu",
        "Beaucoup",
    ]


def test_normalize_ligatures():
    assert normalize("C’est au cœur de ma formation") == "c'est au coeur de ma formation"


def test_order_by_keywords_start_of_label():
    vals = ["Insatisfaisante - x", "Satisfaisante - y", "Très satisfaisante - z", "Moyennement satisfaisante"]
    assert order_by_keywords(vals, ["^tres satisfaisante", "^satisfaisante", "^moyennement", "^insatisfaisante"]) == [
        "Très satisfaisante - z",
        "Satisfaisante - y",
        "Moyennement satisfaisante",
        "Insatisfaisante - x",
    ]
