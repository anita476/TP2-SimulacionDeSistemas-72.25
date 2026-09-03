#!/usr/bin/env python3
"""Grafica la fracción S media en función del tiempo a partir de un archivo agregado."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import matplotlib

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.plot_style import BLUE, VERMILLION, new_figure, place_legend_below, save_figure, style_axes
from utils.stationary import find_stationary


def read_s(path: Path) -> tuple[list[int], list[float], list[float]]:
    """Lee las columnas t, average_s y std_s de un archivo agregado."""
    times: list[int] = []
    averages: list[float] = []
    deviations: list[float] = []

    with path.open(encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(
            (line for line in stream if line.strip() and not line.lstrip().startswith("#")),
            delimiter=" ",
            skipinitialspace=True,
        )
        required_columns = {"t", "average_s", "std_s"}
        if not rows.fieldnames or not required_columns.issubset(rows.fieldnames):
            raise ValueError(f"{path}: se esperaban las columnas t average_s std_s")

        for line_number, row in enumerate(rows, 2):
            try:
                times.append(int(row["t"]))
                averages.append(float(row["average_s"]))
                deviations.append(float(row["std_s"]))
            except (TypeError, ValueError) as error:
                raise ValueError(f"{path}: dato inválido en la línea {line_number}") from error

    if not times:
        raise ValueError(f"{path}: no hay filas de datos")
    return times, averages, deviations




def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="archivo agregado, por ejemplo data/experiment-output/cluster_s.txt")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="ruta de la imagen de salida (por defecto: la del input con extensión .png)",
    )
    parser.add_argument("--t-min", "--t_min", type=int, help="primer tiempo a graficar (inclusive)")
    parser.add_argument("--t-max", "--t_max", type=int, help="último tiempo a graficar (inclusive)")
    parser.add_argument("--epsilon", type=float, required=True, help="distancia máxima a la media del sufijo desde t* hasta el final")
    parser.add_argument("--epochs", type=int, required=True, help="cantidad mínima de muestras desde t* hasta el final")
    parser.add_argument("--no-std", action="store_true", help="ocultar la banda de desviación")
    args = parser.parse_args()

    try:
        times, averages, deviations =read_s(args.input)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.t_min is not None and args.t_max is not None and args.t_min > args.t_max:
        parser.error("--t-min debe ser menor o igual que --t-max")

    selected = [
        (time, average, deviation)
        for time, average, deviation in zip(times, averages, deviations)
        if (args.t_min is None or time >= args.t_min) and (args.t_max is None or time <= args.t_max)
    ]
    if not selected:
        parser.error("el rango de tiempo elegido no contiene datos")
    times, averages, deviations = map(list, zip(*selected))

    try:
        stationary_time = find_stationary(times, averages, args.epsilon, args.epochs)
    except ValueError as error:
        parser.error(str(error))

    output = args.output or args.input.with_suffix(".png")
    output.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = new_figure()
    ax.plot(times, averages, color=BLUE, zorder=3, label="promedio entre corridas")
    if not args.no_std:
        lower = [max(0.0, average - deviation) for average, deviation in zip(averages, deviations)]
        upper = [min(1.0, average + deviation) for average, deviation in zip(averages, deviations)]
        ax.fill_between(
            times,
            lower,
            upper,
            color=BLUE,
            alpha=0.22,
            linewidth=0,
            zorder=2,
            label="desvío entre corridas",
        )
    if stationary_time is not None:
        ax.axvline(
            stationary_time,
            color=VERMILLION,
            linewidth=1.8,
            linestyle="--",
            zorder=4,
            label=rf"$t^*={stationary_time}$",
        )
    style_axes(ax, "tiempo", "fracción de la componente gigante")
    ax.set_ylim(0.0, 1.0)
    if times:
        ax.set_xlim(times[0], times[-1])
    place_legend_below(ax, ncol=2)
    save_figure(fig, output)
    if stationary_time is None:
        print("no se encontró tiempo estacionario")
    else:
        print(f"tiempo estacionario: {stationary_time}")


if __name__ == "__main__":
    main()