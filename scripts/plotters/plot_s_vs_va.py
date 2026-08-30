#!/usr/bin/env python3
"""Punto (e): polarizacion escalar en funcion de la fraccion del cluster mas grande

Un punto = un valor de eta con coordenadas (<S>,<va>) promediadas desde t* (estacionario) hasta el final de la corrida

t* se elige a ojo observando las evoluciones temporales y se usa con --t-stat [t*]
"""


from __future__ import annotations

import argparse
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from matplotlib.lines import Line2D
from matplotlib.ticker import FixedFormatter, FixedLocator

from utils.plot_style import new_figure, place_legend_below, save_figure, style_axes
# Las series (color y símbolo por densidad, relleno y trazo por modelo) y los escalares
# desde t* son los mismos que en los puntos (c) y (d), así que salen de utils/sweeps.py.
from utils.sweeps import Case, Point, collect_points, load_case, pair_t_stats, series_style, sort_cases


def write_summary(path: Path, rows: list[tuple[Case, list[Point]]]) -> None:
    """Deja escalares en texto para poder citarlos sin volver a correr el plotter."""
    lines = [
        "# punto (e): cada fila es un punto de la figura va vs S",
        "# los escalares se promedian desde t_stat (elegido a ojo) hasta el final de la corrida",
        "# el error es el desvío entre realizaciones promediado en esa misma ventana",
        "modelo rho eta t_stat S S_err va va_err",
    ]
    for case, points in rows:
        for p in points:
            lines.append(
                f"{case.model} {case.rho:g} {p.eta:g} {case.t_stat} "
                f"{p.s:.6g} {p.s_err:.6g} {p.va:.6g} {p.va_err:.6g}"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"se escribió {path}")
    
    
    
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", dest="input_dirs", action="append", type=Path, required=True,
                        metavar="DIR", help="barrido en ruido de una densidad y un modelo; repetible")
    parser.add_argument("--t-stat", "--t_stat", dest="t_stats", action="append", type=int, required=True,
                        metavar="T", help="inicio del estacionario de ese barrido; uno por --input-dir, o uno solo para todos")
    parser.add_argument("--output", type=Path, default=Path("data/figuras/va_vs_s.png"))
    parser.add_argument("--out-txt", type=Path, default=None,
                        help="resumen txt (por defecto: el del --output con extensión .txt)")
    parser.add_argument("--x", choices=("s", "va"), default="s",
                        help="qué observable va en el eje x; 's' es lo que pide el enunciado")
    parser.add_argument("--log", action="store_true",
                        help="escala logarítmica en el eje de la polarización (guía 2.4.7)")
    parser.add_argument("--s-lim", "--s_lim", type=float, nargs=2, default=None, metavar=("MIN", "MAX"),
                        help="rango del eje de S; por defecto se ajusta a los datos")

    args = parser.parse_args()

    t_stats = pair_t_stats(parser, args.input_dirs, args.t_stats)

    for directory in args.input_dirs:
        if not directory.is_dir():
            parser.error(f"{directory}: no es un directorio")

    cases = sort_cases([load_case(directory, t_stat) for directory, t_stat in zip(args.input_dirs, t_stats)])
    rows = [(case, collect_points(case)) for case in cases]
    rows = [(case, points) for case, points in rows if points]
    if not rows:
        raise SystemExit("ningún barrido aportó puntos")

    fig, ax = new_figure(width=7.8, height=6.0)
    handles: list[Line2D] = []
    s_en_x = args.x == "s"
    un_solo_modelo = len({case.model for case, _ in rows}) == 1

    for case, points in rows:
        style = series_style(case)
        color, dash = style["color"], style["linestyle"]
        filled = case.model == "vicsek"
        s, s_err = [p.s for p in points], [p.s_err for p in points]
        va, va_err = [p.va for p in points], [p.va_err for p in points]
        x, xerr, y, yerr = (s, s_err, va, va_err) if s_en_x else (va, va_err, s, s_err)

        # Las barras van finas, translúcidas y por detrás de los símbolos, para no tapar
        # las curvas; heredan el trazo de su serie para distinguir los dos modelos.
        bars = ax.errorbar(x, y, xerr=xerr, yerr=yerr, fmt="none", ecolor=color,
                           elinewidth=0.9, capsize=2.5 if filled else 0, alpha=0.45, zorder=2)
        for collection in bars[2]:
            collection.set_linestyle(dash)
        # Los puntos se unen en orden de eta, que es el parámetro que recorre la curva.
        ax.plot(x, y, zorder=3, **style)
        handles.append(
            Line2D([], [], label=case.rho_label if un_solo_modelo else case.label, **style)
        )

    etiqueta = {"s": "fracción de la componente gigante", "va": "polarización"}
    style_axes(ax, etiqueta[args.x], etiqueta["va" if s_en_x else "s"])


    if args.s_lim is not None:
        s_lim = tuple(args.s_lim)
    else:
        low = min(p.s - p.s_err for _, points in rows for p in points)
        margin = max(0.004, 0.08 * (1.0 - low))
        s_lim = (low - margin, 1.0 + margin)

    if s_en_x:
        ax.set_xlim(*s_lim)
        if args.log:
            ax.set_yscale("log")
        else:
            ax.set_ylim(0.0, 1.02)
    else:
        ax.set_ylim(*s_lim)
        if args.log:
            ax.set_xscale("log")
        else:
            ax.set_xlim(0.0, 1.02)

    if args.log:
        eje = ax.yaxis if s_en_x else ax.xaxis
        eje.set_minor_locator(FixedLocator([0.05, 0.2, 0.5]))
        eje.set_minor_formatter(FixedFormatter(
            [r"$5\times10^{-2}$", r"$2\times10^{-1}$", r"$5\times10^{-1}$"]))
        ax.tick_params(axis="y" if s_en_x else "x", which="minor",
                       labelsize=15, length=4, width=1.0)


    # Ídem sweeps.py: una fila con un solo modelo; con los dos, una fila por modelo.
    if un_solo_modelo:
        orden, ncol = handles, len(handles)
    else:
        mitad = len(handles) // 2
        orden = [h for par in zip(handles[:mitad], handles[mitad:]) for h in par]
        ncol = mitad
    place_legend_below(fig, orden, [h.get_label() for h in orden], ncol=ncol)
    save_figure(fig, args.output)
    write_summary(args.out_txt or args.output.with_suffix(".txt"), rows)


if __name__ == "__main__":
    main()