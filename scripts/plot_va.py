#!/usr/bin/env python3
"""Grafica la polarización media en función del tiempo a partir de un archivo agregado."""

from __future__ import annotations
from utils.stationary import find_stationary

import argparse
import csv
from pathlib import Path

from utils.plot_style import BLUE, VERMILLION, new_figure, place_legend_below, save_figure, style_axes


def read_va(path: Path) -> tuple[list[int], list[float], list[float]]:
    """Lee las columnas t, average_va y std_va de un archivo agregado."""
    times: list[int] = []
    averages: list[float] = []
    deviations: list[float] = []

    with path.open(encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(
            (line for line in stream if line.strip() and not line.lstrip().startswith("#")),
            delimiter=" ",
            skipinitialspace=True,
        )
        required_columns = {"t", "average_va", "std_va"}
        if not rows.fieldnames or not required_columns.issubset(rows.fieldnames):
            raise ValueError(f"{path}: se esperaban las columnas t average_va std_va")

        for line_number, row in enumerate(rows, 2):
            try:
                times.append(int(row["t"]))
                averages.append(float(row["average_va"]))
                deviations.append(float(row["std_va"]))
            except (TypeError, ValueError) as error:
                raise ValueError(f"{path}: dato inválido en la línea {line_number}") from error

    if not times:
        raise ValueError(f"{path}: no hay filas de datos")
    return times, averages, deviations


def scalar_average(times: list[int], averages: list[float], stationary_time: int) -> float:
    values = [average for time, average in zip(times, averages) if time >= stationary_time]
    if not values:
        raise ValueError(f"no hay muestras con t >= {stationary_time}")
    return sum(values) / len(values)


def slice_va(
    times: list[int],
    averages: list[float],
    deviations: list[float],
    t_min: int | None,
    t_max: int | None,
) -> tuple[list[int], list[float], list[float]]:
    selected = [
        (time, average, deviation)
        for time, average, deviation in zip(times, averages, deviations)
        if (t_min is None or time >= t_min) and (t_max is None or time <= t_max)
    ]
    if not selected:
        raise ValueError("el rango de tiempo elegido no contiene datos")
    sliced_times, sliced_averages, sliced_deviations = map(list, zip(*selected))
    return sliced_times, sliced_averages, sliced_deviations


def plot_va_on_ax(
    ax,
    times: list[int],
    averages: list[float],
    deviations: list[float],
    stationary_time: int | None,
    show_std: bool = True,
    vline_with_time: bool = True,
    legend: bool = True,
    color: str = BLUE,
    vline_color: str = VERMILLION,
    linestyle: str = "-",
    label: str = "promedio entre corridas",
    std_label: str | None = "desvío entre corridas",
    show_vline: bool = True,
    apply_limits: bool = True,
) -> None:
    ax.plot(times, averages, color=color, linestyle=linestyle, zorder=3, label=label)
    if show_std:
        lower = [max(0.0, average - deviation) for average, deviation in zip(averages, deviations)]
        upper = [min(1.05, average + deviation) for average, deviation in zip(averages, deviations)]
        fill_kwargs = dict(color=color, alpha=0.18 if std_label is None else 0.22, linewidth=0, zorder=2)
        if std_label is not None:
            fill_kwargs["label"] = std_label
        ax.fill_between(times, lower, upper, **fill_kwargs)
    if show_vline and stationary_time is not None:
        line_label = "inicio del estacionario"
        if vline_with_time:
            line_label = rf"{line_label} ($t={stationary_time}$)"
        ax.axvline(stationary_time, color=vline_color, linewidth=1.8, linestyle="--", zorder=4, label=line_label)
    style_axes(ax, "tiempo (s)", "polarización")
    if apply_limits:
        ax.set_ylim(0.0, 1.05)
        if times:
            ax.set_xlim(times[0], times[-1])
    if legend:
        place_legend_below(ax, ncol=2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="archivo agregado, por ejemplo data/experiment-output/va.txt")
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
        times, averages, deviations = read_va(args.input)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.t_min is not None and args.t_max is not None and args.t_min > args.t_max:
        parser.error("--t-min debe ser menor o igual que --t-max")

    try:
        stationary_time = find_stationary(times, averages, args.epsilon, args.epochs)
    except ValueError as error:
        parser.error(str(error))

    try:
        times, averages, deviations = slice_va(times, averages, deviations, args.t_min, args.t_max)
    except ValueError as error:
        parser.error(str(error))

    output = args.output or args.input.with_suffix(".png")
    output.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = new_figure()
    plot_va_on_ax(ax, times, averages, deviations, stationary_time, show_std=not args.no_std)
    save_figure(fig, output)
    if stationary_time is None:
        print("no se encontró tiempo estacionario")
    else:
        print(f"tiempo estacionario: {stationary_time}")
        print(f"va escalar (t >= {stationary_time}): {scalar_average(times, averages, stationary_time):.6g}")


if __name__ == "__main__":
    main()