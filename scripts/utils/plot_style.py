"""Estilo académico compartido para las figuras del TP2.

Sigue la guía de presentaciones: sin título interno, ejes en palabras,
fuente ≥ 20, notación 10^{n} (no 1e-3) y puntos visibles en
las curvas de input vs observable.
Otros:
- axis grids: off
"""

from __future__ import annotations

from contextlib import contextmanager
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


def eta_colors(n: int) -> list:
    """n colores de una rampa morado -> magenta -> rosa para el ruido.

    La corrección pide "del azul al rojo pasando por el verde", pero azul, verde y
    bermellón son los tres colores fijos de la densidad (`COLOR_BY_RHO`): reusarlos
    haría que el mismo color signifique densidad en una figura y ruido en la de al
    lado.  Esta rampa no toca ninguno de los tres y cumple lo que la corrección
    buscaba, que era que las series se distinguieran entre sí.
    """
    cmap = plt.get_cmap("plasma")
    if n == 1:
        return [cmap(0.35)]
    return [cmap(0.15 + 0.55 * i / (n - 1)) for i in range(n)]
MARKERS = ("o", "s", "D", "^", "v", "P")


MODELS = ("vicsek", "voter")
MODEL_LABELS = {"vicsek": "Vicsek", "voter": "votante"}
MODEL_LINESTYLES = {"vicsek": "-", "voter": (0, (1.8, 1.8))}
MODEL_LINEWIDTHS = {"vicsek": 1.7, "voter": 1.7}


EVOLUTION_SIZE = (9.0, 6.5)
EVOLUTION_FONT_SCALE = 1.15
EVOLUTION_LINE_WIDTH = 1.2
# Negro: el rojo se confundia con la serie de rho = 4 (bermellon) y con el
# extremo de la rampa de ruido.  La vertical no es un dato, es una referencia.
EVOLUTION_TSTAR_COLOR = "black"

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


@contextmanager
def scaled_style(font_scale: float = 1.0, line_width: float | None = None):
    """Ajusta fuentes y grosor de línea para una figura de tamaño distinto al estándar.

    Una figura más ancha se achica más al meterla en la diapositiva, así que la fuente
    tiene que crecer algo para no quedar por debajo de los 20 pt de la Guía 1.8.  Pero
    no conviene escalarla con el ancho: si la figura se ensancha más de lo que se
    estira, una fuente escalada por el ancho queda desproporcionada respecto del alto.

    `line_width` va aparte y no acompaña a la fuente: en una serie con miles de puntos
    ruidosos, una línea gruesa se empasta y tapa el patrón.
    """
    apply_academic_style()  # antes del contexto: adentro se revertiría al salir
    size = FONT_SIZE * font_scale
    overrides = {
        "font.size": size,
        "axes.labelsize": size,
        "axes.titlesize": size,
        "xtick.labelsize": size,
        "ytick.labelsize": size,
        "legend.fontsize": size,
    }
    if line_width is not None:
        overrides["lines.linewidth"] = line_width
    with matplotlib.rc_context(overrides):
        yield


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
    ax.grid(False)
    ax.set_axisbelow(True)
    # Del rcParam y no de FONT_SIZE, para no pisar lo que fijó scaled_style().
    ax.tick_params(
        axis="both",
        which="major",
        direction="out",
        top=False,
        right=False,
        labelsize=matplotlib.rcParams["xtick.labelsize"],
    )
    ax.minorticks_off()
    for spine in ax.spines.values():
        spine.set_color("black")
        spine.set_linewidth(matplotlib.rcParams["axes.linewidth"])


def apply_sci_axis(ax, axis: str = "y", scilimits: tuple[int, int] = (-2, 4)) -> None:
    ax.ticklabel_format(axis=axis, style="sci", scilimits=scilimits, useMathText=True)
    offset = ax.yaxis.get_offset_text() if axis == "y" else ax.xaxis.get_offset_text()
    offset.set_fontsize(FONT_SIZE)
    offset.set_fontfamily("serif")


def _center_legend_on_axes(fig) -> None:
    """Corre la leyenda para que quede centrada bajo los ejes, no bajo la figura.
    """
    if not fig.legends or not fig.axes:
        return
    caja = fig.axes[0].get_position()
    centro = caja.x0 + 0.5 * caja.width
    for leyenda in fig.legends:
        bb = leyenda.get_window_extent().transformed(fig.transFigure.inverted())
        # El ancla es la caja que ya ocupa, corrida en x.  Y el loc pasa a "center":
        # con "outside lower center" matplotlib la reubica dentro del ancla y se
        # sube encima del rótulo del eje x.
        leyenda.set_loc("center")
        leyenda.set_bbox_to_anchor(
            (bb.x0 + centro - (bb.x0 + 0.5 * bb.width), bb.y0, bb.width, bb.height),
            transform=fig.transFigure)


def save_figure(fig, path: Path) -> None:
    apply_academic_style()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    fig.set_layout_engine("none")
    _center_legend_on_axes(fig)
    fig.savefig(path, dpi=SAVE_DPI, bbox_inches="tight", pad_inches=0.12, facecolor="white")
    plt.close(fig)
    print(f"se escribió {path}")
