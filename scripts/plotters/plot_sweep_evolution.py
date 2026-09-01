#!/usr/bin/env python3
"""Evolución temporal de un observable, tomada del barrido en ruido.

* varios `--eta` sobre un mismo barrido  -> un color por ruido (ciclo del ruido)
* varios `--input-dir` con un solo `--eta` -> un color por densidad (ciclo de la densidad)
* los dos modelos                          -> línea llena Vicsek, de trazos votante

Para $v_a$ del punto (b) está `va_evolution_runner.py`, que simula con `--stride 1`. Éste
reusa el barrido de (c) y (d), que es de dónde sale el único `S(t)` que hay.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from matplotlib.lines import Line2D

from utils.plot_style import (
    EVOLUTION_FONT_SCALE,
    EVOLUTION_LINE_WIDTH,
    EVOLUTION_SIZE,
    EVOLUTION_TSTAR_COLOR,
    MODEL_LABELS,
    MODEL_LINESTYLES,
    SERIES,
    apply_sci_axis,
    eta_colors,
    new_figure,
    place_legend_below,
    save_figure,
    scaled_style,
    style_axes,
)
from utils.sweeps import (
    COLOR_BY_RHO,
    Case,
    eta_dirs,
    load_case,
    pair_t_stats,
    read_aggregate,
    sort_cases,
)

OBSERVABLES = {
    # nombre -> (archivo agregado, columna, etiqueta del eje y, límites)
    "va": ("va.txt", "va", "polarización", (0.0, 1.02)),
    # Autoescala: con la banda de desvío el rango real llega a ~0.8 y un límite fijo
    # recortaría; los propios números del eje avisan que S se mueve poco.
    "s": ("cluster_s.txt", "s", "fracción de la componente gigante", None),
}


class Serie(NamedTuple):
    """Una curva: los datos y de qué caso salieron, para armar la etiqueta después."""

    case: Case
    eta: float
    times: list[int]
    values: list[float]
    stds: list[float]


def collect_series(case: Case, etas: list[float] | None, observable: str) -> list[Serie]:
    archivo, columna = OBSERVABLES[observable][:2]
    series: list[Serie] = []
    for eta, directory in eta_dirs(case):
        if etas is not None and not any(abs(eta - pedido) < 1e-9 for pedido in etas):
            continue
        try:
            times, averages, stds = read_aggregate(directory / archivo, columna)
        except (OSError, ValueError) as error:
            print(f"se omite {directory}: {error}")
            continue
        series.append(Serie(case, eta, times, averages, stds))
    return series


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", dest="input_dirs", action="append", type=Path, required=True,
                        metavar="DIR", help="barrido en ruido de una densidad y un modelo; repetible")
    parser.add_argument("--t-stat", "--t_stat", dest="t_stats", action="append", type=int, required=True,
                        metavar="T", help="inicio del estacionario; uno por --input-dir, o uno solo para todos")
    parser.add_argument("--eta", type=float, nargs="+", default=None,
                        help="ruidos a dibujar (por defecto: todos los del barrido)")
    parser.add_argument("--observable", choices=tuple(OBSERVABLES), default="va")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    t_stats = pair_t_stats(parser, args.input_dirs, args.t_stats)
    for directory in args.input_dirs:
        if not directory.is_dir():
            parser.error(f"{directory}: no es un directorio")

    cases = sort_cases([load_case(d, t) for d, t in zip(args.input_dirs, t_stats)])
    series = [serie for case in cases for serie in collect_series(case, args.eta, args.observable)]
    if not series:
        raise SystemExit("ningún barrido aportó series")

    etas = sorted({serie.eta for serie in series})
    rhos = sorted({serie.case.rho for serie in series})
    modelos = [name for name in MODEL_LABELS if any(s.case.model == name for s in series)]
    # Un umbral por barrido: sólo los de los que efectivamente aportaron series.
    umbrales = sorted({serie.case.t_stat for serie in series})
    # El color va a la variable que se está estudiando; el modelo, siempre al trazo.
    color_por_eta = len(etas) > 1
    _, _, ylabel, ylim = OBSERVABLES[args.observable]

    with scaled_style(EVOLUTION_FONT_SCALE, line_width=EVOLUTION_LINE_WIDTH):
        fig, ax = new_figure(*EVOLUTION_SIZE)
        for serie in series:
            case = serie.case
            color = (eta_colors(len(etas))[etas.index(serie.eta)] if color_por_eta
                     else COLOR_BY_RHO.get(case.rho, SERIES[rhos.index(case.rho) % len(SERIES)]))
            ax.plot(serie.times, serie.values, color=color,
                    linestyle=MODEL_LINESTYLES[case.model] if len(modelos) > 1 else "-", zorder=3)
            # La banda es el desvío entre corridas, igual que en las figuras de va. Como
            # los observables están acotados en [0, 1], recortamos la banda antes de dibujar
            # para que no se vea "saliendo" del rango físico ni deje un padding visible.
            lower = [max(0.0, min(1.0, v - d)) for v, d in zip(serie.values, serie.stds)]
            upper = [max(0.0, min(1.0, v + d)) for v, d in zip(serie.values, serie.stds)]
            ax.fill_between(serie.times, lower, upper, color=color, alpha=0.18, linewidth=0, zorder=2)

        for t_stat in umbrales:
            ax.axvline(t_stat, color=EVOLUTION_TSTAR_COLOR, linestyle=":",
                       linewidth=EVOLUTION_LINE_WIDTH * 1.5, zorder=4)

        style_axes(ax, "tiempo", ylabel)
        # Guia 1.9, y el mismo x10^3 que las figuras de va del ciclo del ruido.
        apply_sci_axis(ax, "x", scilimits=(3, 3))
        ax.set_ylim(0.0, 1.0)
        ax.margins(y=0.0)
        ax.set_xlim(min(s.times[0] for s in series), max(s.times[-1] for s in series))

        # La leyenda sólo nombra lo que varía: los parámetros constantes van al costado de
        # la figura, en la diapositiva.
        entradas: list[tuple[Line2D, str]] = []
        if color_por_eta:
            entradas += [(Line2D([], [], color=eta_colors(len(etas))[i], linestyle="-"),
                          rf"$\eta={eta:g}$") for i, eta in enumerate(etas)]
        elif len(rhos) > 1:
            entradas += [(Line2D([], [], color=COLOR_BY_RHO.get(rho, SERIES[i % len(SERIES)]),
                                 linestyle="-"), rf"$\rho={rho:g}$")
                         for i, rho in enumerate(rhos)]
        if len(modelos) > 1:
            entradas += [(Line2D([], [], color="0.35", linestyle=MODEL_LINESTYLES[name]),
                          MODEL_LABELS[name]) for name in modelos]
        # t* NO va en la leyenda: es constante y se explica al costado de la figura.
        # Handle largo: el trazo del votante es un guión de 12 pt y con el ancho por
        # defecto la muestra de la leyenda no llega a mostrarlo.
        place_legend_below(fig, [h for h, _ in entradas], [l for _, l in entradas],
                           ncol=min(len(entradas), 5), handlelength=3.0)
        save_figure(fig, args.output)


if __name__ == "__main__":
    main()
