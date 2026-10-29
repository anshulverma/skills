#!/usr/bin/env python3
"""Shared figure helpers for study, learnings and takeaways figures (and the experiments timeline).

Colours and the `_figure` html block come from render_tracker, so every tab draws in one palette.
Generators live beside their PNGs in the run dir and read run files, never /tmp.
"""
import os
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from render_tracker import BLUE, GREY, LIGHT, ORANGE, PURPLE, _figure  # noqa: E402,F401  (re-exported)

BG = "#fcfcfb"


def style(bg: str = BG) -> None:
    """11 pt text, no top/right spines, grey axes, `bg` behind everything."""
    plt.rcParams.update({
        "font.size": 11, "font.family": "Liberation Sans", "figure.facecolor": bg, "axes.facecolor": bg,
        "savefig.facecolor": bg, "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": GREY, "axes.labelcolor": GREY, "xtick.color": GREY, "ytick.color": GREY,
        "axes.titlesize": 11, "legend.frameon": False,
    })


def size(pageless: bool) -> tuple[float, float]:
    """Base figsize per doc: 13x7.5 in pageless, 6.5x3.75 in paged. The width is fixed; the height is a floor.
    delta_band and the experiments timeline grow taller with arms or sub-rows rather than overlap bars, so a
    figure's aspect can drift; tabs.py then re-inserts it with a fresh frame (figure_frame_reset, apply exit 5)."""
    return (13.0, 7.5) if pageless else (6.5, 3.75)


def save(fig, path: str, dpi: int = 150) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fig.savefig(path, dpi=dpi, facecolor=fig.get_facecolor(), metadata={"Software": None})
    plt.close(fig)
    return path


def dot(src: str, png: str) -> str:
    """Render graphviz source text to `png`; the .dot sits beside it for reruns."""
    path = os.path.splitext(png)[0] + ".dot"
    with open(path, "w") as f:
        f.write(src)
    subprocess.run(["dot", "-Tpng", "-Gdpi=150", path, "-o", png], check=True)
    return png


def delta_band(arms: dict, baseline_mean: float, baseline_sd: float, out: str, threshold: float | None = None,
               pageless: bool = True) -> str:
    """Each arm's delta against the baseline: one dot per seed, a bar at the mean, the baseline's +/-1 and
    +/-2 sd noise band shaded, and an optional threshold line. `arms` maps name -> value or [values]."""
    style()
    names = list(arms)
    w, _ = size(pageless)
    fig, ax = plt.subplots(figsize=(w, max(2.0, 0.9 + 0.4 * len(names))))
    for k, a in ((2, 0.12), (1, 0.22)):
        ax.axvspan(-k * baseline_sd, k * baseline_sd, color=GREY, alpha=a, lw=0)
    ax.axvline(0, color=GREY, lw=1)
    for i, name in enumerate(names):
        vals = arms[name] if isinstance(arms[name], (list, tuple)) else [arms[name]]
        d = [v - baseline_mean for v in vals]
        mean = sum(d) / len(d)
        colour = BLUE if abs(mean) > 2 * baseline_sd else GREY
        ax.scatter(d, [i] * len(d), color=colour, s=18, alpha=0.6, zorder=3)
        ax.plot([mean, mean], [i - 0.3, i + 0.3], color=colour, lw=3, zorder=4)
        ax.annotate(f"{mean:+.4g}", (mean, i), xytext=(0, 9), textcoords="offset points", ha="center",
                    fontsize=9, color=colour)
    if threshold is not None:
        ax.axvline(threshold, color=ORANGE, ls="--", lw=1.5, label=f"threshold {threshold:+g}")
        ax.legend(loc="lower right", fontsize=9)
    ax.set_yticks(range(len(names)), names)
    ax.set_ylim(len(names) - 0.4, -0.6)
    ax.set_xlabel(f"delta vs baseline {baseline_mean:.4g} (shaded: baseline noise, 1 and 2 sd = {baseline_sd:.3g})")
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    return save(fig, out)
