#!/usr/bin/env python3
"""Plot average S over time from an aggregated S data file."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from utils.find_stationary import find_stationary
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_va(path: Path) -> tuple[list[int], list[float], list[float]]:
    """Read t, average_s, and std_s columns from an aggregate file."""
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
            raise ValueError(f"{path}: expected columns t average_s std_s")

        for line_number, row in enumerate(rows, 2):
            try:
                times.append(int(row["t"]))
                averages.append(float(row["average_s"]))
                deviations.append(float(row["std_s"]))
            except (TypeError, ValueError) as error:
                raise ValueError(f"{path}: invalid data at line {line_number}") from error

    if not times:
        raise ValueError(f"{path}: no data rows")
    return times, averages, deviations




def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="aggregate file, such as data/experiment-output/cluster_s.txt")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="output image path (default: input path with a .png suffix)",
    )
    parser.add_argument("--t-min", "--t_min", type=int, help="first time to plot (inclusive)")
    parser.add_argument("--t-max", "--t_max", type=int, help="last time to plot (inclusive)")
    parser.add_argument("--epsilon", type=float, required=True, help="maximum distance from the mean of t* to the end")
    parser.add_argument("--epochs", type=int, required=True, help="minimum samples from t* to the end")
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
    ax.plot(times, averages, color="#176b87", linewidth=2, label="average S")
    if stationary_time is not None:
        ax.axvline(stationary_time, color="red", linewidth=1.5, label=f"inicio del estacionario t={stationary_time}")
        ax.axvspan(stationary_time, times[-1], color="#d62728", alpha=0.06, zorder=0)
    if not args.no_std:
        lower = [average - deviation for average, deviation in zip(averages, deviations)]
        upper = [average + deviation for average, deviation in zip(averages, deviations)]
        ax.fill_between(times, lower, upper, color="#8ecae6", alpha=0.35, label="std S")
    ax.set_xlabel("t")
    ax.set_ylabel("average S")
    ax.set_title("Average S over time")
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