"""Plotting helpers shared by the notebooks (matplotlib).

Rules applied everywhere:
- one colour for a simple measure (blue); two series = blue + orange;
- an ordered scale = a single hue from light to dark (no good/bad judgement);
- "Je ne sais pas" / "Sans avis" = grey, always last;
- the base (number of respondents) is written on every chart;
- thin bars, discreet grid, percentages written on the bars.

Every plotting function accepts `ax=` so that several panels can be composed in one figure.

"""

from __future__ import annotations

import textwrap
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.colors import LinearSegmentedColormap, PowerNorm, to_hex
from matplotlib.patches import Polygon

import geo

BLUE = "#2a78d6"
ORANGE = "#eb6834"
GREY = "#b9b8b1"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e0"
_RAMP = LinearSegmentedColormap.from_list("ramp", ["#d3e4f8", "#2a78d6", "#123a70"])

# Global switch for the error bars (95 % CI). Each call to `bars` can override it with ci=True/False.
SHOW_CI = True

# Normalised fragments that identify a "no opinion" answer (drawn in grey, placed last).
NO_OPINION_WORDS = (
    "je ne sais pas",
    "ne souhaite pas",
    "prefere ne pas",
    "sans avis",
    "ne mange pas",
    "ne sais pas",
)


def _ascii_lower(x):
    """Lower-case ASCII version of `x` (accents removed, apostrophes straightened)."""
    s = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()
    return s.replace("’", "'")


def is_no_opinion(label):
    """True if the answer label means "no opinion / don't know / prefer not to say"."""
    n = _ascii_lower(label)
    return any(w in n for w in NO_OPINION_WORDS)


def blue_ramp(n):
    """`n` shades of blue, from light to dark."""
    if n <= 1:
        return [BLUE]
    return [to_hex(_RAMP(0.1 + 0.8 * i / (n - 1))) for i in range(n)]


def apply_style():
    """Set the matplotlib defaults used by every chart (fonts, spines, colours)."""
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "font.size": 9.5,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK2,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "xtick.color": INK2,
            "ytick.color": INK,
            "text.color": INK,
            "axes.titlesize": 10.5,
            "axes.titleweight": "bold",
        }
    )


apply_style()


def _wrap(text, width=42):
    """Wrap a label over several lines."""
    return "\n".join(textwrap.wrap(str(text), width)) or str(text)


def _title(ax, title, base=None, note=None):
    """Bold title on the left + small grey subtitle (base and note) just above the axes."""
    sub = []
    if base is not None:
        sub.append(f"base : {int(base):,} répondant·es".replace(",", " "))
    if note:
        sub.append(note)
    ax.set_title(_wrap(title, 70), loc="left", pad=22 if sub else 8)
    if sub:
        ax.annotate(
            "\n".join(textwrap.wrap(" · ".join(sub), 110)),
            (0, 1),
            xytext=(0, 4),
            textcoords="offset points",
            xycoords="axes fraction",
            fontsize=8.5,
            color=INK2,
            va="bottom",
        )


def _x_grid(ax):
    """Light vertical grid behind the bars, no tick marks."""
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0)


def _get_ax(ax, size):
    """Return `ax`, or create a new figure of the given size when `ax` is None."""
    if ax is None:
        _, ax = plt.subplots(figsize=size)
    return ax


# --------------------------------------------------------------------------
# Simple bars (single choice, multiple choice, rankings)
# --------------------------------------------------------------------------
def bars(
    t,
    label,
    value,
    low=None,
    high=None,
    title="",
    base=None,
    n_max=15,
    sort=True,
    note=None,
    color=BLUE,
    ax=None,
    width=7.5,
    highlight=None,
    ci=None,
):
    """Horizontal bars. `value` is a proportion (0-1); `low`/`high` are the 95 % CI bounds columns.

    `ci`: True/False to show the error bars or not (default: the global switch `SHOW_CI`).
    `sort=False` keeps the table order (scales, age brackets). `highlight`: {label: colour}.
    """
    if t is None or len(t) == 0:
        raise ValueError(
            f"Aucune donnée à tracer pour « {title} ». La question n'a pas été reconnue avec ce type : "
            "vérifiez son type (choix unique ou multiple) et le format de l'export."
        )
    if not (SHOW_CI if ci is None else ci):
        low = high = None
    t = t.copy()
    if sort:
        t = t.sort_values(value, ascending=False)
    t = t.head(n_max).iloc[::-1]
    ax = _get_ax(ax, (width, 0.36 * len(t) + 1.5))
    labels = [_wrap(x) for x in t[label]]
    colours = [(highlight or {}).get(x, color) for x in t[label]]
    ax.barh(labels, t[value] * 100, height=0.62, color=colours)
    if low is not None and high is not None:
        err = [((t[value] - t[low]).clip(lower=0) * 100).values, ((t[high] - t[value]).clip(lower=0) * 100).values]
        ax.errorbar(t[value] * 100, labels, xerr=err, fmt="none", ecolor=INK2, elinewidth=0.9, capsize=2)
    x_max = (t[high] if high is not None else t[value]).max() * 100
    for y, v in enumerate(t[value] * 100):
        x = (t[high].iloc[y] * 100 if high is not None else v) + x_max * 0.015
        ax.text(x, y, f"{v:.0f} %", va="center", fontsize=8.5, color=INK)
    ax.set_xlim(0, x_max * 1.15)
    ax.set_xlabel("% des répondant·es")
    _x_grid(ax)
    _title(ax, title, base, note)
    return ax


# --------------------------------------------------------------------------
# 100 % stacked bars (ordered scales, matrices)
# --------------------------------------------------------------------------
def stacked(t, row, category, pct, order=None, base="base", title="", note=None, ax=None, width=8.5):
    """One 100 % bar per `row`. `pct` is a proportion. `order`: categories from negative to positive.

    "No opinion" categories are drawn in grey, at the end.
    """
    cats = list(dict.fromkeys(t[category]))
    if order:
        cats = [c for c in order if c in cats] + [c for c in cats if c not in order]
    with_opinion = [c for c in cats if not is_no_opinion(c)]
    no_opinion = [c for c in cats if is_no_opinion(c)]
    cats = with_opinion + no_opinion
    colours = dict(zip(with_opinion, blue_ramp(len(with_opinion))))
    colours.update({c: GREY for c in no_opinion})

    rows = list(dict.fromkeys(t[row]))
    wide = t.pivot_table(index=row, columns=category, values=pct, aggfunc="sum").reindex(rows)
    wide = wide.reindex(columns=cats).fillna(0)
    total = wide.sum(axis=1).replace(0, np.nan)
    wide = wide.div(total, axis=0) * 100  # renormalise so each bar sums to exactly 100
    bases = t.groupby(row)[base].max().reindex(rows) if base in t else None

    ax = _get_ax(ax, (width, 0.62 * len(rows) + 2.0))
    y = np.arange(len(rows))[::-1]
    left = np.zeros(len(rows))
    for c in cats:
        v = wide[c].values
        ax.barh(y, v, left=left, height=0.62, color=colours[c], edgecolor="white", linewidth=1.2, label=_wrap(c, 28))
        for yi, vi, li in zip(y, v, left):
            if vi >= 7:  # write the value only when the segment is wide enough
                dark = colours[c] != GREY and _luminance(colours[c]) < 0.45
                ax.text(
                    li + vi / 2, yi, f"{vi:.0f}", ha="center", va="center", fontsize=8.5, color="white" if dark else INK
                )
        left = left + np.nan_to_num(v)
    ticks = [
        _wrap(x, 40) + (f"\n(n = {int(bases[x])})" if bases is not None and pd.notna(bases[x]) else "") for x in rows
    ]
    ax.set_yticks(y)
    ax.set_yticklabels(ticks)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% des répondant·es de la ligne")
    _x_grid(ax)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=min(len(cats), 4),
        frameon=False,
        fontsize=8.5,
        handlelength=1,
        columnspacing=1.2,
    )
    _title(ax, title, None, note)
    return ax


def _luminance(hex_colour):
    """Perceived luminance (0 = black, 1 = white) of a "#rrggbb" colour."""
    r, g, b = (int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# --------------------------------------------------------------------------
# Grouped bars (several series compared on the same categories)
# --------------------------------------------------------------------------
def grouped(
    t, category, series, value, series_order=None, title="", base=None, note=None, n_max=15, ax=None, width=8.5
):
    """One bar per series and per category; categories sorted by the first series.

    Two series: blue and orange. Three or more (ordered, e.g. age brackets): blue shades, light to dark.
    """
    names = series_order or list(dict.fromkeys(t[series]))
    wide = t.pivot_table(index=category, columns=series, values=value, aggfunc="sum").reindex(columns=names).fillna(0)
    wide = wide.sort_values(names[0], ascending=False).head(n_max).iloc[::-1]
    ax = _get_ax(ax, (width, 0.28 * len(names) * len(wide) + 1.8))
    h = 0.68 / len(names)
    colours = (BLUE, ORANGE) if len(names) == 2 else blue_ramp(len(names))
    y = np.arange(len(wide))
    for i, (s, c) in enumerate(zip(names, colours)):
        shift = ((len(names) - 1) / 2 - i) * h
        v = wide[s].values * 100
        ax.barh(y + shift, v, height=h * 0.92, color=c, label=s)
        for yi, vi in zip(y + shift, v):
            ax.text(vi + 0.6, yi, f"{vi:.0f}", va="center", fontsize=8, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels([_wrap(x, 38) for x in wide.index])
    ax.set_xlabel("% des répondant·es")
    ax.set_xlim(0, wide.max().max() * 100 * 1.12)
    _x_grid(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=min(len(names), 4), frameon=False, fontsize=8.5)
    _title(ax, title, base, note)
    return ax


# --------------------------------------------------------------------------
# Helpers to build tables and figures
# --------------------------------------------------------------------------
def long_from_tables(tables, questions, labels, key="question", category="réponse", pct="%"):
    """Long table (row, category, pct, base) built from the frequency tables of several questions.

    `tables`: frequency tables stacked in one frame; `labels`: {question: short label for the row}.
    """
    pieces = []
    for q in questions:
        sub = tables[tables[key].astype(str) == str(q)]
        if sub.empty:
            continue
        pieces.append(
            pd.DataFrame(
                {
                    "row": labels.get(q, f"Q{q}"),
                    "category": sub[category].values,
                    "pct": sub[pct].values,
                    "base": sub["base"].values,
                }
            )
        )
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(columns=["row", "category", "pct", "base"])


def panels(n, ncols=2, width=6.2, height=3.4):
    """Grid of `n` panels; returns (figure, list of usable axes)."""
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(width * ncols, height * nrows))
    axes = np.atleast_1d(axes).ravel()
    for extra in axes[n:]:
        extra.axis("off")
    return fig, list(axes[:n])


def save_figure(fig, name, folder, enabled=True):
    """Save the figure as PNG when `enabled`. Returns the path, or None."""
    if not enabled:
        return None
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    return path


# --------------------------------------------------------------------------
# Map of France (départements or régions)
# --------------------------------------------------------------------------
_OVERSEAS = ["971", "972", "973", "974", "976"]  # département codes drawn as small insets
_METRO_BOX = (-5.4, 9.8, 41.2, 51.2)  # lon min, lon max, lat min, lat max
_IDF_BOX = (1.4, 3.65, 48.05, 49.3)
_NO_DATA = "#e6e5e0"  # light grey: below the display threshold


def _label_point(polygons):
    """Centroid of the largest outer ring of a (multi)polygon (area-weighted, shoelace formula)."""
    best, best_area = None, -1.0
    for poly in polygons:
        ring = np.array(poly[0])
        x, y = ring[:, 0], ring[:, 1]
        cross = x[:-1] * y[1:] - x[1:] * y[:-1]
        area = cross.sum() / 2
        if abs(area) > best_area and abs(area) > 0:
            best, best_area = (
                (((x[:-1] + x[1:]) * cross).sum() / (6 * area), ((y[:-1] + y[1:]) * cross).sum() / (6 * area)),
                abs(area),
            )
    return best


def _draw_shapes(ax, items, values, min_n, norm, cmap, labels, label_fn, fontsize, linewidth=0.5, skip_labels=()):
    """Fill every shape of `items` according to `values`; grey when below `min_n`. Writes the labels."""
    patches, colours = [], []
    for it in items:
        n = int(values.get(it["code"], 0))
        for poly in it["polygons"]:
            patches.append(Polygon(np.array(poly[0]), closed=True))
            colours.append(cmap(norm(n)) if n >= min_n else _NO_DATA)
    ax.add_collection(PatchCollection(patches, facecolors=colours, edgecolors="white", linewidths=linewidth))
    if labels:
        for it in items:
            n = int(values.get(it["code"], 0))
            if n < min_n or it["code"] in skip_labels:
                continue
            x, y = _label_point(it["polygons"])
            dark = _luminance(to_hex(cmap(norm(n)))) < 0.45
            ax.text(
                x,
                y,
                label_fn(it, n),
                ha="center",
                va="center",
                fontsize=fontsize,
                color="white" if dark else INK,
                linespacing=0.95,
            )


def _frame(ax, box):
    """Set the view box and a roughly undistorted aspect (longitude degrees shrink with latitude)."""
    x0, x1, y0, y1 = box
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect(1 / np.cos(np.radians((y0 + y1) / 2)))
    ax.axis("off")


def map_france(counts, level="department", title="", min_n=None, labels=True, base=None, note=None, size=(8.6, 8.4)):
    """Map of France coloured by number of answers.

    `counts`: Series of answers per département code (from `geo.count_by_department`).
    `level`: "department" or "region" (counts are summed per région). Overseas territories are drawn as insets;
    at département level, a zoom on Île-de-France is added because Paris and its petite couronne are tiny.
    `min_n`: shapes below this count are drawn in grey and not labelled (small groups are never shown;
    default 10 for départements and 20 for régions). Returns the figure.
    """
    data = geo.load_geography()
    by_region = level == "region"
    values = geo.count_by_region(counts) if by_region else counts
    items = data["regions"] if by_region else data["departments"]
    min_n = min_n if min_n is not None else (20 if by_region else 10)
    shown = values[values >= min_n]
    vmax = max(int(shown.max()) if len(shown) else 1, 2)
    norm = PowerNorm(0.5, vmin=min_n, vmax=vmax)  # square-root scale: Paris would otherwise flatten the rest
    cmap = _RAMP
    names = geo.names(level)

    def label_fn(it, n):
        return f"{_wrap(names[it['code']], 14)}\n{n}" if by_region else str(n)

    overseas_codes = _OVERSEAS if not by_region else ["01", "02", "03", "04", "06"]
    metro = [i for i in items if i["code"] not in overseas_codes]
    idf_codes = {i["code"] for i in metro if i.get("region") == "11"}  # labelled in the zoom instead
    fig = plt.figure(figsize=size)
    ax = fig.add_axes([0.0, 0.14, 0.74 if not by_region else 0.8, 0.78])
    _draw_shapes(
        ax, metro, values, min_n, norm, cmap, labels, label_fn, 7.5 if by_region else 6.2, skip_labels=idf_codes
    )
    _frame(ax, _METRO_BOX)

    if not by_region:  # Île-de-France zoom (département level only)
        zoom = fig.add_axes([0.66, 0.5, 0.34, 0.4])
        idf = [i for i in metro if i["region"] == "11"]
        _draw_shapes(zoom, idf, values, min_n, norm, cmap, labels, lambda it, n: f"{it['code']}\n{n}", 7.5, 0.8)
        _frame(zoom, _IDF_BOX)
        zoom.text(
            _IDF_BOX[0], _IDF_BOX[3], "Zoom Île-de-France", fontsize=8.5, fontweight="bold", va="bottom", color=INK
        )

    # overseas insets, bottom row
    for k, code in enumerate(overseas_codes):
        it = next(i for i in items if i["code"] == code)
        sub = fig.add_axes([0.02 + k * 0.145, 0.03, 0.13, 0.1])
        _draw_shapes(sub, [it], values, min_n, norm, cmap, labels, lambda it, n: str(n), 7.5)
        xs = np.concatenate([np.array(p[0]) for p in it["polygons"]])
        pad = 0.15
        _frame(sub, (xs[:, 0].min() - pad, xs[:, 0].max() + pad, xs[:, 1].min() - pad, xs[:, 1].max() + pad))
        sub.set_title(names[code], fontsize=7.5, color=INK2, pad=1)

    # colour bar + grey legend
    cax = fig.add_axes([0.74, 0.06, 0.24, 0.018])
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    ticks = sorted({min_n, max(min_n, vmax // 4), max(min_n, vmax // 2), vmax})
    cb.set_ticks(ticks)
    cb.ax.tick_params(labelsize=7.5, length=2, color=INK2)
    cb.outline.set_visible(False)
    cax.set_title("nombre de réponses", fontsize=8, color=INK2, pad=3)
    fig.patches.append(
        plt.Rectangle((0.74, 0.1), 0.02, 0.018, transform=fig.transFigure, facecolor=_NO_DATA, edgecolor="none")
    )
    fig.text(0.765, 0.109, f"moins de {min_n} réponses (non affiché)", fontsize=7.5, color=INK2, va="center")

    sub_parts = [f"base : {int(base):,} répondant·es".replace(",", " ")] if base is not None else []
    if note:
        sub_parts.append(note)
    fig.text(0.0, 0.985, _wrap(title, 80), fontsize=10.5, fontweight="bold", va="top", ha="left")
    if sub_parts:
        fig.text(0.0, 0.945, " · ".join(sub_parts), fontsize=8.5, color=INK2, va="top", ha="left")
    return fig
