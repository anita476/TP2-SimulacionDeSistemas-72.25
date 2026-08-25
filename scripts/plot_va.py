#!/usr/bin/env python3
"""Plot average VA over time from an aggregated VA data file."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_va(path: Path) -> tuple[list[int], list[float], list[float]]:
    """Read t, average_va, and std_va columns from an aggregate file."""
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
            raise ValueError(f"{path}: expected columns t average_va std_va")

        for line_number, row in enumerate(rows, 2):
            try:
                times.append(int(row["t"]))
                averages.append(float(row["average_va"]))
                deviations.append(float(row["std_va"]))
            except (TypeError, ValueError) as error:
                raise ValueError(f"{path}: invalid data at line {line_number}") from error

    if not times:
        raise ValueError(f"{path}: no data rows")
    return times, averages, deviations


def find_stationary(times: list[int], averages: list[float], epsilon: float, epochs: int) -> int | None:
    """Return the first t whose next epochs averages are within epsilon of their mean."""
    if epsilon < 0:
        raise ValueError("epsilon must be non-negative")
    if epochs < 1:
        raise ValueError("epochs must be at least 1")

    for index in range(len(averages) - epochs + 1):
        window = averages[index : index + epochs]
        window_average = sum(window) / epochs
        if all(abs(value - window_average) <= epsilon for value in window):
            return times[index]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="aggregate file, such as data/experiment-output/va.txt")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="output image path (default: input path with a .png suffix)",
    )
    parser.add_argument("--t-min", "--t_min", type=int, help="first time to plot (inclusive)")
    parser.add_argument("--t-max", "--t_max", type=int, help="last time to plot (inclusive)")
    parser.add_argument("--epsilon", type=float, required=True, help="maximum distance from the local average")
    parser.add_argument("--epochs", type=int, required=True, help="number of consecutive averages to check")
    parser.add_argument("--no-std", action="store_true", help="hide the standard-deviation band")
    args = parser.parse_args()

    try:
        times, averages, deviations = read_va(args.input)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.t_min is not None and args.t_max is not None and args.t_min > args.t_max:
        parser.error("--t-min must be less than or equal to --t-max")

    selected = [
        (time, average, deviation)
        for time, average, deviation in zip(times, averages, deviations)
        if (args.t_min is None or time >= args.t_min) and (args.t_max is None or time <= args.t_max)
    ]
    if not selected:
        parser.error("the selected time range contains no data")
    times, averages, deviations = map(list, zip(*selected))

    try:
        stationary_time = find_stationary(times, averages, args.epsilon, args.epochs)
    except ValueError as error:
        parser.error(str(error))

    output = args.output or args.input.with_suffix(".png")
    output.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(times, averages, color="#176b87", linewidth=2, label="average VA")
    if stationary_time is not None:
        ax.axvline(stationary_time, color="red", linewidth=1.5, label=f"stationary t={stationary_time}")
    if not args.no_std:
        lower = [average - deviation for average, deviation in zip(averages, deviations)]
        upper = [average + deviation for average, deviation in zip(averages, deviations)]
        ax.fill_between(times, lower, upper, color="#8ecae6", alpha=0.35, label="std VA")
    ax.set_xlabel("t")
    ax.set_ylabel("average VA")
    ax.set_title("Average VA over time")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"wrote {output}")
    if stationary_time is None:
        print("no stationary time found")
    else:
        print(f"stationary time: {stationary_time}")


if __name__ == "__main__":
    main()