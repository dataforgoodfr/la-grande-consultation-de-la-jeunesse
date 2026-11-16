"""Geography helpers: department codes, response counts by département / région.

No plotting here (see `charts.map_france`) and no heavy dependency: the boundaries are read from
`resources/geo/france.json`, built once by `tools/build_geo.py`.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

GEO_FILE = Path(__file__).resolve().parent.parent / "resources" / "geo" / "france.json"


@lru_cache(maxsize=1)
def load_geography():
    """Read the simplified boundaries: {"departments": [...], "regions": [...]} (cached)."""
    with open(GEO_FILE, encoding="utf-8") as f:
        return json.load(f)


def department_code(label):
    """Département code from a questionnaire label ("75 - Paris" -> "75", "2A - Corse-du-Sud" -> "2A").

    Returns None when no code can be read. Single digits are zero-padded ("1 - Ain" -> "01").
    """
    if label is None or pd.isna(label):
        return None
    m = re.match(r"^\s*(2[AaBb]|\d{1,3})\s*(?:[-–—:]|$)", str(label))
    if not m:
        return None
    code = m.group(1).upper()
    return code.zfill(2) if code.isdigit() else code


def count_by_department(labels):
    """Number of answers per département code. `labels`: a Series of "75 - Paris"-like answers.

    Returns a Series indexed by code (all the départements of the map, 0 when nobody answered).
    Answers whose code is not a known département are ignored and counted in `.attrs["unknown"]`.
    """
    geo = load_geography()
    known = [d["code"] for d in geo["departments"]]
    codes = pd.Series(labels).map(department_code)
    counts = codes[codes.isin(known)].value_counts().reindex(known, fill_value=0).astype(int)
    counts.attrs["unknown"] = int(
        (codes.notna() & ~codes.isin(known)).sum() + (codes.isna() & pd.Series(labels).notna()).sum()
    )
    return counts


def count_by_region(dept_counts):
    """Sum the département counts into régions. Returns a Series indexed by region code."""
    geo = load_geography()
    region_of = {d["code"]: d["region"] for d in geo["departments"]}
    by_region = dept_counts.groupby(dept_counts.index.map(region_of)).sum()
    return by_region.reindex([r["code"] for r in geo["regions"]], fill_value=0).astype(int)


def names(level="department"):
    """{code: name} for the départements or the régions."""
    geo = load_geography()
    return {x["code"]: x["name"] for x in geo["departments" if level == "department" else "regions"]}
