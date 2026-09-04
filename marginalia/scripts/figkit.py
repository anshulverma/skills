"""Figure and equation rendering for marginalia companion docs.

There is no matplotlib in the devserver python. Run scripts that import this through a
Bento kernel:

    bento console --kernel bento_kernel_ads_generative_retrieval --file /tmp/myfigs.py

Import it by adding the skill's scripts dir to sys.path first:

    import sys; sys.path.insert(0, "/home/<user>/.claude/skills/marginalia/scripts")
    from figkit import *

    fig, ax = canvas(14, 6)
    headline(ax, "What changed", "One line of context.")
    # leave the top ~12 units clear for the headline block; start content below y=85
    box(ax, 6, 40, 40, 20, "Fresh rows", ["computed this step"], fc=tint(FRESH, .88), ec=FRESH)
    arrow(ax, (46, 50), (54, 50))
    save(fig, "01_overview")

    equation(r"r = \\exp\\left(\\log \\pi_\\theta(a) - \\log \\pi_{\\text{old}}(a)\\right)", "eq_ratio")

Colors come from a validated categorical palette (all pairs clear the CVD and
normal-vision separation floors in light mode). Assign them by *meaning* and keep that
assignment fixed across every figure in a doc — a reader learns "orange = the new path"
once, and it has to stay true on the next figure. Never pick a color by rank order.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

# ---------------------------------------------------------------- surfaces & ink
SURFACE = "#fcfcfb"   # chart surface
PLANE = "#f9f9f7"     # page plane, for recessed panels
INK = "#0b0b0b"       # primary text
INK2 = "#52514e"      # secondary text
MUTED = "#898781"     # axis labels, asides
GRID = "#e1e0d9"      # hairline gridlines
RULE = "#c3c2b7"      # baselines, box borders

# --------------------------------------------- categorical slots, in fixed order
# The ORDER is the colorblind-safety mechanism, not decoration. Take slots from the
# top; do not reorder, and do not invent a 9th - fold extras into "Other" or facet.
BLUE = "#2a78d6"      # slot 1
ORANGE = "#eb6834"    # slot 2
AQUA = "#1baf7a"      # slot 3
YELLOW = "#eda100"    # slot 4
MAGENTA = "#e87ba4"   # slot 5
GREEN = "#008300"     # slot 6
VIOLET = "#4a3aa7"    # slot 7
RED = "#e34948"       # slot 8

# Convenience aliases for a two-thing comparison, the most common companion-doc figure.
BEFORE = BLUE
AFTER = ORANGE
FRESH = AQUA
DELAYED = YELLOW

# ------------------------------------------------- status, never reused as series
GOOD = "#0ca30c"
WARN = "#fab219"
SERIOUS = "#ec835a"
CRIT = "#d03b3b"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "figure.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "mathtext.fontset": "cm",  # Computer Modern: the LaTeX look
    }
)

OUTDIR = "/tmp"
SAVED = []


def tint(hex_color, amount):
    """Blend toward white. 0.9 gives a pale fill that keeps its hue identity."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % tuple(
        int(c + (255 - c) * amount) for c in (r, g, b)
    )


def canvas(w=14.0, h=8.0):
    """A 0-100 x 0-100 coordinate space with no axes. Position things by percentage.

    One vertical unit is NOT one horizontal unit unless w == h, so anything that must
    look round has to correct for the aspect - `dot()` does. If you add a shape helper,
    prefer ax.plot markers (sized in points) over data-space radii.
    """
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.set_position([0, 0, 1, 1])
    ax._figkit_hw = (h, w)
    return fig, ax


def _vscale(ax):
    """Vertical units per 'one unit on a reference 8in-tall canvas'.

    A 4-unit gap is comfortable at 8in tall and a collision at 5in, because the
    coordinate space is 0-100 whatever the physical height. Scale vertical gaps by
    this so spacing looks the same on any canvas.
    """
    h, _ = getattr(ax, "_figkit_hw", (8.0, 14.0))
    return 8.0 / h


def headline(ax, text, sub=None, y=95.5):
    ax.text(3, y, text, fontsize=20, fontweight="bold", color=INK, va="top")
    if sub:
        ax.text(3, y - 4.6 * _vscale(ax), sub, fontsize=11.5, color=INK2, va="top")


def box(
    ax, x, y, w, h, title=None, lines=None, fc=SURFACE, ec=RULE, tc=INK, lc=INK2,
    ts=12, ls=9.6, lw=1.4, align="center", radius=1.2, title_dy=None,
):
    """Rounded box anchored at its lower-left corner.

    `lines` are secondary text under the title. With lines the title sits at the top;
    without them it centers.
    """
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0,rounding_size=%s" % radius,
            linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2,
        )
    )
    tx, ha = (x + w / 2.0, "center") if align == "center" else (x + 1.6, "left")
    n = len(lines) if lines else 0
    if title is not None:
        dy = title_dy if title_dy is not None else (h / 2.0 if n == 0 else 2.4)
        ax.text(
            tx, y + h - dy, title, fontsize=ts, color=tc, ha=ha,
            va="center" if n == 0 else "top", fontweight="bold", zorder=4,
        )
    if lines:
        top = y + h - (5.4 if title is not None else 2.6)
        for i, ln in enumerate(lines):
            ax.text(tx, top - i * (ls * 0.30), ln, fontsize=ls, color=lc,
                    ha=ha, va="top", zorder=4)


def chip(ax, x, y, text, color, fs=9.2):
    """A solid pill. Use for labels that name a whole column or path."""
    ax.text(
        x, y, text, fontsize=fs, color="white", ha="center", va="center",
        fontweight="bold", zorder=6,
        bbox=dict(boxstyle="round,pad=0.55", facecolor=color, edgecolor="none"),
    )


def arrow(ax, p0, p1, color=INK2, lw=2.0, style="-|>", ls="-", rad=0.0, ms=14):
    ax.add_patch(
        FancyArrowPatch(
            p0, p1, arrowstyle=style, mutation_scale=ms, linewidth=lw, color=color,
            linestyle=ls, connectionstyle="arc3,rad=%s" % rad, zorder=3,
            shrinkA=1, shrinkB=1,
        )
    )


def note(ax, x, y, text, color=INK2, fs=9.4, ha="left", va="center",
         italic=False, bold=False):
    ax.text(x, y, text, fontsize=fs, color=color, ha=ha, va=va,
            style="italic" if italic else "normal",
            fontweight="bold" if bold else "normal", zorder=5)


def band(ax, x, y, w, h, color, label, fs=10.5, label_top=True):
    """A tinted full-width strip for a takeaway. Label sits at the top so a note
    placed inside the band below it does not collide."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.9",
            linewidth=0, facecolor=tint(color, 0.86), zorder=1,
        )
    )
    ly = y + h - 2.8 if label_top else y + h / 2.0
    ax.text(x + 1.4, ly, label, fontsize=fs, color=color, fontweight="bold",
            va="center", ha="left", zorder=4)


def dot(ax, x, y, color, size=15, label=None, tc="white", fs=8.5):
    """A round marker. `size` is in POINTS, so it stays circular on any canvas
    aspect - a Circle patch in data coords would render as an ellipse."""
    ax.plot(x, y, marker="o", markersize=size, color=color, linestyle="none",
            zorder=4, clip_on=False)
    if label:
        ax.text(x, y, label, fontsize=fs, color=tc, ha="center", va="center",
                fontweight="bold", zorder=5)


def footer(ax, text):
    ax.text(3, 1.8, text, fontsize=8.6, color=MUTED, va="center")


def save(fig, name, dpi=170):
    path = "%s/fig_%s.png" % (OUTDIR, name)
    fig.savefig(path, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    SAVED.append(path)
    print("wrote", path)
    return path


def equation(tex, name, fontsize=22, color=INK, pad=0.35, dpi=220):
    """Render a standalone LaTeX equation to a tightly-cropped PNG.

    `tex` is mathtext (a LaTeX subset) WITHOUT surrounding $ - they are added here.
    Escape backslashes, or use a raw string:

        equation(r"\\mathcal{L} = -\\min(r\\hat{A},\\ \\mathrm{clip}(r,1-\\epsilon,1+\\epsilon)\\hat{A})", "eq_ppo")

    Supported: \\frac \\sum \\prod \\int \\sqrt, greek, sub/superscripts, \\mathcal
    \\mathbb \\mathrm \\text \\mathit, \\left(...\\right), \\qquad, \\frac.
    NOT supported, and it RAISES rather than degrading: \\textit, \\textbf, \\underbrace (use \\text or
    \\mathit), \\begin{align}, \\begin{cases}, custom macros. Note \\text{} cannot nest math -
    write \\text{(}\\Delta\\text{ in steps)}, not \\text{($\\Delta$ in steps)}. For multi-line math render one image per line and
    stack them, or fall back to a monospace <pre> block in the ghtml.

    Insert the result at 60-75% of text width so it reads as display math, not a figure.
    """
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, "$%s$" % tex, fontsize=fontsize, color=color)
    path = "%s/%s.png" % (OUTDIR, name)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=pad,
                facecolor=SURFACE)
    plt.close(fig)
    SAVED.append(path)
    print("wrote", path)
    return path


def png_size(path):
    """(width, height) in px, straight from the PNG header - no PIL on this box.

    Use it to compute the --height that preserves aspect at --width 468:
        w, h = png_size(p); height = round(468 * h / w)
    """
    import struct

    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    return struct.unpack(">II", head[16:24])
