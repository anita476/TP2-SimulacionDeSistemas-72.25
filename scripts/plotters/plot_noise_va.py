#!/usr/bin/env python3
"""Punto (c): polarización escalar en función del ruido.

Un punto = un valor de eta para el cual se toman todas las muestras desde t* (estacionario)
hasta el final de todas las realizaciones del barrido; la barra de error es el desvío
estándar de ese conjunto de muestras.

t* se elige a ojo mirando las evoluciones temporales del punto (b) y se pasa con
`--t-stat`. Cada `--input-dir` es un barrido (un modelo y una densidad) y entra como una
serie más de la misma figura, que es lo que pide el punto (f).
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
    "# punto (c): cada fila es un punto de la figura va vs eta",
    "# va se calcula sobre todas las muestras desde t_stat hasta el final de todas las realizaciones",
    "# va_err es el desvío estándar de esas muestras en el estacionario",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", dest="input_dirs", action="append", type=Path, required=True,
                        metavar="DIR", help="barrido en ruido de una densidad y un modelo; repetible")
    parser.add_argument("--t-stat", "--t_stat", dest="t_stats", action="append", type=int, required=True,
                        metavar="T", help="inicio del estacionario de ese barrido; uno por --input-dir, o uno solo para todos")
    parser.add_argument("--output", type=Path, default=Path("data/figuras/va_vs_eta.png"))
    parser.add_argument("--out-txt", type=Path, default=None,
                        help="resumen txt (por defecto: el del --output con extensión .txt)")
    parser.add_argument("--log", action="store_true",
                        help="escala logarítmica en el eje de la polarización (guía 2.4.7)")
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
        plot_scalar_vs_eta(
            subset, output,
            ylabel="polarización",
            value=lambda point: point.va,
            error=lambda point: point.va_err,
            ylim=None if args.log else (0.0, 1.02),
            log=args.log,
        )

    dibujar(rows, args.output)
    write_eta_summary(
        args.out_txt or args.output.with_suffix(".txt"), rows,
        SUMMARY_HEADER, "modelo rho eta t_stat va va_err",
        lambda point: (point.va, point.va_err),
    )

    # Las de un solo modelo son de apoyo: con seis series encimadas cuesta seguir una sola.
    # Van aparte para no mezclarse con la comparada, que es la que pide el punto (f).
    models = [name for name in MODEL_LABEL if any(case.model == name for case, _ in rows)]
    if args.no_per_model or len(models) < 2:
        return
    per_model_dir = args.per_model_dir or (args.output.parent / "por-modelo")
    for model in models:
        subset = [(case, points) for case, points in rows if case.model == model]
        dibujar(subset, per_model_dir / f"{args.output.stem}_{model}.png")


if __name__ == "__main__":
    main()
