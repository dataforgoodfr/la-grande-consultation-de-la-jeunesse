"""Helpers shared by the analysis scripts (grande_consultation.py).

Contents: text normalisation, ordering helpers, splitting of multi-choice answers,
and the Wilson confidence interval used everywhere.
User-facing strings (warnings, column labels) stay in French on purpose: they end up in reports.
"""

import re
import unicodedata

import numpy as np
import pandas as pd


def normalize(s):
    """Lower-case, strip accents, straighten apostrophes, collapse spaces: used to compare labels."""
    s = unicodedata.normalize(
        "NFKD", str(s).lower().replace("’", "'").replace("‘", "'").replace("œ", "oe").replace("æ", "ae")
    )
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def order_by_list(values, order):
    """Sort `values` following the exact list `order`; values missing from `order` go last."""
    order = order or []
    return [v for v in order if v in values] + [v for v in values if v not in order]


def order_by_keywords(values, keywords):
    """Sort `values` by (normalised) keywords; anything else goes last, alphabetically.

    A keyword prefixed with "^" must match the START of the label
    (avoids "satisfaisante" matching inside "insatisfaisante").
    """
    keywords = keywords or []

    def key(v):
        n = normalize(v)
        for i, kw in enumerate(keywords):
            if n.startswith(kw[1:]) if kw.startswith("^") else kw in n:
                return (i, n)
        return (len(keywords), n)

    return sorted(values, key=key)


def split_outside_parentheses(value, clean=None):
    """Split "A, B (x, y), C" on the commas that are NOT inside parentheses.

    `clean` (optional) is applied to every piece, e.g. to group the free-text "Autre : …" answers.
    """
    if pd.isna(value):
        return []
    parts, depth, cur = [], 0, ""
    for ch in str(value):
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    parts = [p for p in parts if p]
    return [clean(p) for p in parts] if clean else parts


def wilson(k, n, z=1.96):
    """Wilson confidence interval (95 % by default) for a proportion k/n. Returns (low, high)."""
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / den
    margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return (max(0, centre - margin), min(1, centre + margin))

