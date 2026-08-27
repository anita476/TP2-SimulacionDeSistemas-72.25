"""Estilo académico compartido para las figuras del TP2.

Sigue la guía de presentaciones: sin título interno, ejes en palabras con
unidades MKS, fuente ≥ 20, notación 10^{n} (no 1e-3) y puntos visibles en
las curvas de input vs observable.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

FONT_SIZE = 20
FIGURE_SIZE = (6.5, 5.4)
SAVE_DPI = 300

# Wong, Nature Methods 8, 441 (2011): paleta distinguible con daltonismo.
BLUE = "#0072B2"
VERMILLION = "#D55E00"
GREEN = "#009E73"
PURPLE = "#CC79A7"
ORANGE = "#E69F00"
NAVY = "#332288"
SERIES = (BLUE, VERMILLION, GREEN, PURPLE, ORANGE, NAVY)
MARKERS = ("o", "s", "D", "^", "v", "P")

_APPLIED = False


def apply_academic_style() -> None:
    global _APPLIED
    if _APPLIED:
        return
    matplotlib.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": FONT_SIZE,
            "axes.labelsize": FONT_SIZE,
            "axes.titlesize": FONT_SIZE,
            "axes.linewidth": 1.15,
            "axes.formatter.use_mathtext": True,
            "axes.formatter.limits": (-2, 4),
            "xtick.labelsize": FONT_SIZE,
            "ytick.labelsize": FONT_SIZE,
            "xtick.major.size": 6,
            "ytick.major.size": 6,
            "xtick.major.width": 1.1,
            "ytick.major.width": 1.1,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.fontsize": FONT_SIZE,
            "legend.frameon": True,
            "legend.fancybox": False,
            "legend.edgecolor": "0.35",
            "legend.framealpha": 1.0,
            "legend.borderpad": 0.4,
            "legend.handlelength": 1.6,
            "mathtext.fontset": "stix",
            "lines.linewidth": 1.8,
            "lines.markersize": 8.5,
            "errorbar.capsize": 4.5,
            "grid.alpha": 0.28,
            "grid.linewidth": 0.7,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "figure.constrained_layout.h_pad": 0.08,
            "figure.constrained_layout.w_pad": 0.06,
            "savefig.dpi": SAVE_DPI,
            "savefig.pad_inches": 0.2,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    _APPLIED = True


def new_figure(width: float | None = None, height: float | None = None):
    apply_academic_style()
    return plt.subplots(
        figsize=(FIGURE_SIZE[0] if width is None else width, FIGURE_SIZE[1] if height is None else height),
        layout="constrained",
    )


def place_legend_below(target, *args, ncol: int = 1, **kwargs):
    """Leyenda debajo de los ejes, sin tapar la etiqueta x.

    `loc='outside lower center'` solo existe en leyendas de figura; si
    llega un Axes, se mueven los handles al Figure.
    """
    kwargs.setdefault("loc", "outside lower center")
    kwargs.setdefault("ncol", ncol)
    kwargs.setdefault("frameon", True)
    if not args and hasattr(target, "get_legend_handles_labels"):
        args = target.get_legend_handles_labels()
        target = target.figure
    return target.legend(*args, **kwargs)


def style_axes(ax, xlabel: str, ylabel: str) -> None:
    ax.set_xlabel(xlabel, labelpad=10)
    ax.set_ylabel(ylabel, labelpad=10)
    ax.grid(True, which="major")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", which="major", direction="out", top=False, right=False, labelsize=FONT_SIZE)
    ax.minorticks_off()
    for spine in ax.spines.values():
        spine.set_color("black")
        spine.set_linewidth(1.15)


def apply_sci_axis(ax, axis: str = "y") -> None:
    ax.ticklabel_format(axis=axis, style="sci", scilimits=(-2, 4), useMathText=True)
    offset = ax.yaxis.get_offset_text() if axis == "y" else ax.xaxis.get_offset_text()
    offset.set_fontsize(FONT_SIZE)
    offset.set_fontfamily("serif")


def save_figure(fig, path: Path) -> None:
    apply_academic_style()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    fig.savefig(path, dpi=SAVE_DPI, bbox_inches="tight", pad_inches=0.12, facecolor="white")
    plt.close(fig)
    print(f"se escribió {path}")
