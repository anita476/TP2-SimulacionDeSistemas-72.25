#!/usr/bin/env python3
"""Punto (d): fracción de la componente gigante en función del ruido.

Para cada eta, el punto se calcula usando todas las muestras estacionarias de todas las
realizaciones del barrido; el error de la barra es el desvío estándar de ese conjunto.

Cada `--input-dir` es un barrido (un modelo y una densidad) y entra como una serie más de
la misma figura, que es lo que pide el punto (f).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.sweeps import (
    MODEL_LABEL,
    collect_points,
    load_case,
    pair_t_stats,
    plot_scalar_vs_eta,
    sort_cases,
    write_eta_summary,
)


SUMMARY_HEADER = [
    "# punto (d): cada fila es un punto de la figura S vs eta",
    "# S se calcula sobre todas las muestras desde t_stat hasta el final de todas las realizaciones",
    "# S_err es el desvío estándar de esas muestras en el estacionario",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", dest="input_dirs", action="append", type=Path, required=True,
                        metavar="DIR", help="barrido en ruido de una densidad y un modelo; repetible")
    parser.add_argument("--t-stat", "--t_stat", dest="t_stats", action="append", type=int, required=True,
                        metavar="T", help="inicio del estacionario de ese barrido; uno por --input-dir, o uno solo para todos")
    parser.add_argument("--output", type=Path, default=Path("data/figuras/s_vs_eta.png"))
    parser.add_argument("--out-txt", type=Path, default=None,
                        help="resumen txt (por defecto: el del --output con extensión .txt)")
    parser.add_argument("--y-lim", "--y_lim", type=float, nargs=2, default=None, metavar=("MIN", "MAX"),
                        help="rango del eje de S; por defecto se ajusta a los datos")
    parser.add_argument("--per-model-dir", type=Path, default=None,
                        help="carpeta para las figuras de un solo modelo (por defecto: por-modelo/ al lado del --output)")
    parser.add_argument("--no-per-model", action="store_true",
                        help="no generar las figuras de un solo modelo")
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

    def dibujar(subset, output):
        # Sin --y-lim el eje se ajusta a los datos: a estas densidades S vive en una franja
        # angosta pegada a 1, y un 0 a 1 fijo deja la figura vacía.
        plot_scalar_vs_eta(
            subset, output,
            ylabel="fracción de la componente gigante",
            value=lambda point: point.s,
            error=lambda point: point.s_err,
            ylim=tuple(args.y_lim) if args.y_lim else None,
        )

    dibujar(rows, args.output)
    write_eta_summary(
        args.out_txt or args.output.with_suffix(".txt"), rows,
        SUMMARY_HEADER, "modelo rho eta t_stat S S_err",
        lambda point: (point.s, point.s_err),
    )

    # Las de un solo modelo son de apoyo, y van al ciclo del ruido de la presentación; la
    # comparada es la del ciclo del votante, que es la que pide el punto (f).
    models = [name for name in MODEL_LABEL if any(case.model == name for case, _ in rows)]
    if args.no_per_model or len(models) < 2:
        return
    per_model_dir = args.per_model_dir or (args.output.parent / "por-modelo")
    for model in models:
        subset = [(case, points) for case, points in rows if case.model == model]
        dibujar(subset, per_model_dir / f"{args.output.stem}_{model}.png")


if __name__ == "__main__":
    main()
