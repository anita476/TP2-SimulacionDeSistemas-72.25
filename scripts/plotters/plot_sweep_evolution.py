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

import matplotlib
from matplotlib.lines import Line2D

from utils.plot_style import (
    EVOLUTION_FONT_SCALE,
    EVOLUTION_LINE_WIDTH,
    EVOLUTION_SIZE,
    EVOLUTION_TSTAR_COLOR,
    EVOLUTION_TSTAR_LINESTYLE,
    EVOLUTION_TSTAR_LINEWIDTH,
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
    _rho_key,
    eta_dirs,
    format_rho,
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
    parser.add_argument("--label-t-stat", "--label_t_stat", nargs="?", const="simbolo",
                        default=None, choices=("simbolo", "valor"), metavar="MODO",
                        help="rotular cada vertical al lado de la línea: 'simbolo' escribe t* y "
                             "el número va al epígrafe (la convención); 'valor' escribe t*=N para "
                             "la diapositiva, que no tiene epígrafe.  Sin el flag va muda")
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
                     else _rho_key(COLOR_BY_RHO, case.rho,
                                   SERIES[rhos.index(case.rho) % len(SERIES)]))
            ax.plot(serie.times, serie.values, color=color,
                    linestyle=MODEL_LINESTYLES[case.model] if len(modelos) > 1 else "-", zorder=3)
            # La banda es el desvío entre corridas, igual que en las figuras de va. Como
            # los observables están acotados en [0, 1], recortamos la banda antes de dibujar
            # para que no se vea "saliendo" del rango físico ni deje un padding visible.
            lower = [max(0.0, min(1.0, v - d)) for v, d in zip(serie.values, serie.stds)]
            upper = [max(0.0, min(1.0, v + d)) for v, d in zip(serie.values, serie.stds)]
            ax.fill_between(serie.times, lower, upper, color=color, alpha=0.18, linewidth=0, zorder=2)

        for t_stat in umbrales:
            ax.axvline(t_stat, color=EVOLUTION_TSTAR_COLOR,
                       linestyle=EVOLUTION_TSTAR_LINESTYLE,
                       linewidth=EVOLUTION_TSTAR_LINEWIDTH, zorder=4)

        style_axes(ax, "tiempo", ylabel)
        # Guia 1.9, y el mismo x10^3 que las figuras de va del ciclo del ruido.
        apply_sci_axis(ax, "x", scilimits=(3, 3))
        ax.set_ylim(0.0, 1.0)
        ax.margins(y=0.0)
        ax.set_xlim(min(s.times[0] for s in series), max(s.times[-1] for s in series))
        # El rótulo va pegado a la línea y no en la leyenda: la vertical no es una serie.
        # Abajo, porque en estas figuras las curvas se amontonan arriba y ahí el rótulo
        # quedaría tapado; y del lado de adentro si t* cae cerca del borde derecho.
        if args.label_t_stat:
            x0, x1 = ax.get_xlim()
            for t_stat in umbrales:
                a_la_derecha = (t_stat - x0) < 0.85 * (x1 - x0)
                texto = rf"$t^*={t_stat:g}$" if args.label_t_stat == "valor" else r"$t^*$"
                ax.annotate(
                    texto,
                    xy=(t_stat, 0.04), xycoords=("data", "axes fraction"),
                    xytext=(7 if a_la_derecha else -7, 0), textcoords="offset points",
                    ha="left" if a_la_derecha else "right", va="center",
                    color=EVOLUTION_TSTAR_COLOR,
                    fontsize=matplotlib.rcParams["xtick.labelsize"],
                    zorder=5,
                )

        # La leyenda sólo nombra lo que varía: los parámetros constantes van al costado de
        # la figura, en la diapositiva.
        entradas: list[tuple[Line2D, str]] = []
        if color_por_eta:
            entradas += [(Line2D([], [], color=eta_colors(len(etas))[i], linestyle="-"),
                          rf"$\eta={eta:g}$") for i, eta in enumerate(etas)]
        elif len(rhos) > 1:
            entradas += [(Line2D([], [], color=_rho_key(COLOR_BY_RHO, rho, SERIES[i % len(SERIES)]),
                                 linestyle="-"), rf"$\rho={format_rho(rho)}$")
                         for i, rho in enumerate(rhos)]
        if len(modelos) > 1:
            entradas += [(Line2D([], [], color="0.35", linestyle=MODEL_LINESTYLES[name]),
                          MODEL_LABELS[name]) for name in modelos]
        # t* nunca va en la leyenda: no es una serie.  Con --label-t-stat se rotula
        # al lado de su propia vertical, arriba del set_xlim.
        # Handle largo: el trazo del votante es un guión de 12 pt y con el ancho por
        # defecto la muestra de la leyenda no llega a mostrarlo.
        place_legend_below(fig, [h for h, _ in entradas], [l for _, l in entradas],
                           ncol=min(len(entradas), 5), handlelength=3.0)
        save_figure(fig, args.output)


if __name__ == "__main__":
    main()
