"""Tests of the plotting functions and of the notebooks' validity (no real data)."""

import ast
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat
import pandas as pd
import pytest

import charts as ch

ROOT = Path(__file__).resolve().parent.parent


def test_is_no_opinion():
    assert ch.is_no_opinion("Je ne sais pas")
    assert ch.is_no_opinion("Sans avis")
    assert not ch.is_no_opinion("Oui, plutôt")


def test_bars_and_stacked():
    t = pd.DataFrame({"r": ["A", "B", "C"], "p": [0.5, 0.3, 0.2], "lo": [0.4, 0.2, 0.1], "hi": [0.6, 0.4, 0.3]})
    ax = ch.bars(t, "r", "p", "lo", "hi", title="Test", base=100)
    assert len(ax.patches) == 3
    plt.close("all")
    long = pd.DataFrame(
        {
            "row": ["Q1"] * 3 + ["Q2"] * 3,
            "category": ["Non", "Oui", "Je ne sais pas"] * 2,
            "pct": [0.2, 0.5, 0.3, 0.4, 0.4, 0.2],
            "base": [10] * 6,
        }
    )
    ax = ch.stacked(long, "row", "category", "pct", order=["Non", "Oui"], title="Test")
    assert len(ax.patches) == 6
    plt.close("all")


def test_grouped():
    t = pd.DataFrame({"c": ["a", "b"] * 2, "s": ["x"] * 2 + ["y"] * 2, "v": [0.3, 0.2, 0.1, 0.4]})
    ax = ch.grouped(t, "c", "s", "v", series_order=["x", "y"], title="Test")
    assert len(ax.patches) == 4
    plt.close("all")


@pytest.mark.parametrize("name", ["gc_graphiques", "grande_consultation"])
def test_notebooks_are_valid(name):
    nb = nbformat.read(ROOT / "notebooks" / f"{name}.ipynb", as_version=4)
    nbformat.validate(nb)
    for cell in nb.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert not cell.outputs, "notebooks are delivered without outputs (personal data)"


def test_bars_ci_switch():
    t = pd.DataFrame({"o": ["a", "b"], "p": [0.4, 0.2], "lo": [0.3, 0.1], "hi": [0.5, 0.3]})
    ax = ch.bars(t, "o", "p", "lo", "hi", title="t", base=10)
    assert len(ax.containers) >= 2  # bars + traits d'erreur
    ax2 = ch.bars(t, "o", "p", "lo", "hi", title="t", base=10, ci=False)
    assert len(ax2.containers) == 1
    ch.SHOW_CI = False
    try:
        assert len(ch.bars(t, "o", "p", "lo", "hi", title="t").containers) == 1
        assert len(ch.bars(t, "o", "p", "lo", "hi", title="t", ci=True).containers) >= 2
    finally:
        ch.SHOW_CI = True


def test_geography_is_consistent():
    import geo

    data = geo.load_geography()
    assert len(data["departments"]) == 101 and len(data["regions"]) == 18
    region_codes = {r["code"] for r in data["regions"]}
    assert all(d["region"] in region_codes for d in data["departments"])
    assert {"2A", "2B", "75", "974"} <= {d["code"] for d in data["departments"]}


def test_department_code_and_counts():
    import geo

    assert geo.department_code("75 - Paris") == "75"
    assert geo.department_code("2a - Corse-du-Sud") == "2A"
    assert geo.department_code("1 - Ain") == "01"
    assert geo.department_code("974 - La Réunion") == "974"
    assert geo.department_code("Paris") is None and geo.department_code(None) is None
    answers = pd.Series(["75 - Paris", "75 - Paris", "92 - Hauts-de-Seine", "99 - ???", None])
    counts = geo.count_by_department(answers)
    assert counts["75"] == 2 and counts["92"] == 1 and counts.sum() == 3 and counts.attrs["unknown"] == 1
    regions = geo.count_by_region(counts)
    assert regions["11"] == 3 and regions.sum() == 3


@pytest.mark.parametrize("level", ["department", "region"])
def test_map_france_draws(level):
    import geo

    counts = geo.count_by_department(
        pd.Series(["75 - Paris"] * 30 + ["13 - Bouches-du-Rhône"] * 12 + ["974 - La Réunion"])
    )
    fig = ch.map_france(counts, level=level, title="Test", base=43)
    assert len(fig.axes) >= 7  # main map, overseas insets, colour bar (+ zoom at département level)
    plt.close("all")


@pytest.mark.parametrize("name", ["gc_graphiques"])
def test_finish_saves_before_showing(name):
    """plt.show() closes the figure in Jupyter: saving afterwards would write a blank image."""
    nb = nbformat.read(ROOT / "notebooks" / f"{name}.ipynb", as_version=4)
    src = next(c.source for c in nb.cells if c.cell_type == "code" and "def finish(" in c.source)
    assert src.index("save_figure") < src.index("plt.show()")
