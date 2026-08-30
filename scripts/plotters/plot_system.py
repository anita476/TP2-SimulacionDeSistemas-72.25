#!/usr/bin/env python3
"""Esquema del sistema simulado: la caja L x L, el radio de interaccion r_c y el contorno periodico.

    python3 scripts/plotters/plot_system.py
    python3 scripts/plotters/plot_system.py --output data/figuras/sistema.png
"""

from __future__ import annotations

import argparse
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle

from utils.plot_style import BLUE, VERMILLION, new_figure, place_legend_below, save_figure

OTHER_FACE = "#d9d9d9"
OTHER_EDGE = "#9e9e9e"
BOX_EDGE = "black"
BOX_LW = 1.4
DIMENSION = "black"
GHOST_ALPHA = 0.28

ARROW_LEN = 0.62  # m; largo de la flecha de velocidad, solo indica la direccion
DOT_SIZE = 46


def toy_configuration(box: float, radius: float, seed: int) -> tuple[np.ndarray, np.ndarray, int, list[int]]:
    """Devuelve (posiciones, angulos, indice de la partícula i, indices de sus vecinas).

    """
    rng = np.random.default_rng(seed)

    target = np.array([3.6, 6.3])
    target_angle = 0.95

    # Vecinas: dentro de r, repartidas en angulo y con direcciones parecidas a la de i.
    # El sector de abajo a la izquierda queda vacío a propósito: por ahí pasa la cota de r.
    offsets = [(0.52, 0.30), (0.80, 1.55), (0.66, 2.70), (0.88, 5.35)]
    neighbour_angles = [0.72, 1.24, 0.88, 1.10]
    neighbours = np.array([[target[0] + d * np.cos(a), target[1] + d * np.sin(a)] for d, a in offsets])

    # Resto: uniformes, pero lejos del anillo para que no quede ninguna ambigua en el borde.
    rest: list[np.ndarray] = []
    while len(rest) < 22:
        candidate = rng.uniform(0.0, box, size=2)
        if np.hypot(*(candidate - target)) < radius + 0.45:
            continue
        rest.append(candidate)

    positions = np.vstack([target, neighbours, np.array(rest)])
    angles = np.concatenate([[target_angle], neighbour_angles, rng.uniform(0.0, 2.0 * np.pi, size=len(rest))])
    return positions, angles, 0, list(range(1, 1 + len(neighbours)))


def draw_particles(ax, positions, angles, colors, *, alpha=1.0, zorder=4) -> None:
    """Un punto en la posicion y una flecha con la direccion de la velocidad."""
    ax.scatter(positions[:, 0], positions[:, 1], s=DOT_SIZE, c=colors,
               edgecolors=OTHER_EDGE, linewidths=0.5, alpha=alpha, zorder=zorder)
    ax.quiver(positions[:, 0], positions[:, 1],
              np.cos(angles) * ARROW_LEN, np.sin(angles) * ARROW_LEN,
              color=colors, alpha=alpha, angles="xy", scale_units="xy", scale=1.0,
              width=0.007, headwidth=4.0, headlength=5.0, headaxislength=4.5,
              pivot="tail", zorder=zorder)


def draw_ghosts(ax, positions, angles, colors, box: float, band: float) -> None:
    """Copias atenuadas de lo que asoma por el otro lado: eso es el contorno periodico."""
    for dx in (-box, 0.0, box):
        for dy in (-box, 0.0, box):
            if dx == 0.0 and dy == 0.0:
                continue
            shifted = positions + np.array([dx, dy])
            inside = ((shifted[:, 0] > -band) & (shifted[:, 0] < box + band)
                      & (shifted[:, 1] > -band) & (shifted[:, 1] < box + band))
            if not inside.any():
                continue
            draw_particles(ax, shifted[inside], angles[inside],
                           [colors[k] for k in np.flatnonzero(inside)],
                           alpha=GHOST_ALPHA, zorder=2)


def annotate_r(ax, center, radius: float, angle: float) -> None:
    """Flecha doble del centro de i al anillo, con la etiqueta r debajo del segmento.

    `angle` apunta al hueco que dejan las vecinas: la cota tiene que cruzar el disco por
    donde no hay ninguna flecha.
    """
    tip = (center[0] + radius * np.cos(angle), center[1] + radius * np.sin(angle))
    ax.annotate("", xy=tip, xytext=tuple(center), zorder=7,
                arrowprops=dict(arrowstyle="<|-|>", color=DIMENSION, linewidth=1.4,
                                shrinkA=0, shrinkB=0, mutation_scale=13))
    # La etiqueta va afuera del disco, prolongando la cota: adentro cae sobre una vecina.
    label = (center[0] + 1.20 * radius * np.cos(angle), center[1] + 1.20 * radius * np.sin(angle))
    ax.text(label[0], label[1], "$r_c$", color=DIMENSION, ha="right", va="top", zorder=7)


def annotate_l(ax, box: float, offset: float) -> None:
    """Las dos cotas de la caja, fuera de la banda de imagenes periodicas."""
    arrow = dict(arrowstyle="<|-|>", color=DIMENSION, linewidth=1.2,
                 shrinkA=0, shrinkB=0, mutation_scale=13)
    ax.annotate("", xy=(box, -offset), xytext=(0.0, -offset), arrowprops=arrow, zorder=6)
    ax.text(0.5 * box, -offset - 0.30, "$L$", ha="center", va="top", zorder=6)
    ax.annotate("", xy=(-offset, box), xytext=(-offset, 0.0), arrowprops=arrow, zorder=6)
    ax.text(-offset - 0.30, 0.5 * box, "$L$", ha="right", va="center", zorder=6)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-L", type=float, default=10.0, help="lado de la caja (m)")
    parser.add_argument("-r", type=float, default=1.0, help="radio de interaccion (m)")
    parser.add_argument("--seed", type=int, default=7, help="semilla de las particulas de relleno")
    parser.add_argument("--output", type=Path, default=Path("data/figuras/sistema.png"))
    args = parser.parse_args()

    positions, angles, target, neighbours = toy_configuration(args.L, args.r, args.seed)
    colors = [OTHER_FACE] * len(positions)
    colors[target] = VERMILLION
    for j in neighbours:
        colors[j] = BLUE

    band = args.r  # ancho de la banda de imagenes periodicas dibujada fuera de la caja
    margin = band + 0.85  # deja lugar para las cotas de L, que van por fuera de la banda

    fig, ax = new_figure(width=7.2, height=6.6)

    ax.add_patch(Rectangle((0, 0), args.L, args.L, fill=False,
                           edgecolor=BOX_EDGE, linewidth=BOX_LW, zorder=5))

    draw_ghosts(ax, positions, angles, colors, args.L, band)

    # El anillo y los segmentos van debajo de las particulas para no taparlas.
    center = positions[target]
    ax.add_patch(Circle(tuple(center), args.r, facecolor=VERMILLION, alpha=0.07, zorder=1))
    ax.add_patch(Circle(tuple(center), args.r, fill=False, edgecolor=VERMILLION,
                        linestyle="--", linewidth=1.5, zorder=3))
    for j in neighbours:
        ax.plot([center[0], positions[j][0]], [center[1], positions[j][1]],
                color=VERMILLION, linewidth=1.0, alpha=0.5, zorder=3)

    draw_particles(ax, positions, angles, colors)

    annotate_r(ax, center, args.r, angle=-2.35)
    annotate_l(ax, args.L, offset=band + 0.35)

    # Sin ejes: es un esquema, y el recuadro de los ejes se lee como una segunda caja.
    # La geometría queda dicha por las cotas de L y r.
    ax.set_aspect("equal")
    ax.set_xlim(-margin, args.L + margin)
    ax.set_ylim(-margin, args.L + margin)
    ax.set_axis_off()

    handles = [
        Line2D([], [], marker="o", linestyle="", markerfacecolor=VERMILLION,
               markeredgecolor=OTHER_EDGE, label="partícula $i$"),
        Line2D([], [], marker="o", linestyle="", markerfacecolor=BLUE,
               markeredgecolor=OTHER_EDGE, label="vecinas de $i$"),
        Line2D([], [], marker="o", linestyle="", markerfacecolor=OTHER_FACE,
               markeredgecolor=OTHER_EDGE, label="resto"),
        Line2D([], [], marker="o", linestyle="", markerfacecolor=OTHER_FACE,
               markeredgecolor=OTHER_EDGE, alpha=GHOST_ALPHA, label="imágenes periódicas"),
    ]
    place_legend_below(fig, handles, [h.get_label() for h in handles], ncol=2)

    save_figure(fig, args.output)


if __name__ == "__main__":
    main()
