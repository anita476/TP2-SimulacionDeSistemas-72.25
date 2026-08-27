#!/usr/bin/env python3
"""Grafica tiempos de búsqueda CIM a partir de cim_timing_runner.py."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.plot_style import MARKERS, SERIES, apply_sci_axis, new_figure, place_legend_below, save_figure, style_axes


SOURCE_STYLE = {
    "tp2": (SERIES[0], MARKERS[0], "-", "TP2, contorno periódico"),
    "tp1": (SERIES[1], MARKERS[1], "--", "TP1, paredes"),
}


def read_aggregate(path: Path) -> list[dict[str, float | int | str]]:
    required = {
        "source",
        "N",
        "L",
        "M",
        "rho",
        "periodic",
        "n_samples",
        "mean_build",
        "std_build",
        "mean_sweep",
        "std_sweep",
        "mean_cim",
        "std_cim",
    }
    rows: list[dict[str, float | int | str]] = []
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(
            (line for line in stream if line.strip() and not line.lstrip().startswith("#")),
            delimiter=" ",
            skipinitialspace=True,
        )
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path}: se esperaban las columnas {' '.join(sorted(required))}")
        for line_number, raw in enumerate(reader, 2):
            try:
                rows.append(
                    {
                        "source": raw["source"],
                        "N": int(raw["N"]),
                        "L": float(raw["L"]),
                        "M": int(raw["M"]),
                        "rho": float(raw["rho"]),
                        "periodic": int(raw["periodic"]),
                        "n_samples": int(raw["n_samples"]),
                        "mean_build": float(raw["mean_build"]),
                        "std_build": float(raw["std_build"]),
                        "mean_sweep": float(raw["mean_sweep"]),
                        "std_sweep": float(raw["std_sweep"]),
                        "mean_cim": float(raw["mean_cim"]),
                        "std_cim": float(raw["std_cim"]),
                    }
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"{path}: dato inválido en la línea {line_number}") from error
    if not rows:
        raise ValueError(f"{path}: no hay filas de datos")
    return rows


def parse_tp2_trace(path: Path) -> tuple[list[float], list[float]]:
    builds: list[float] = []
    sweeps: list[float] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.split()
            if not fields or fields[0].startswith("#") or fields == ["t", "build_seconds", "sweep_seconds"]:
                continue
            if len(fields) != 3:
                raise ValueError(f"{path}: traza CIM inválida en la línea {line_number}: {line!r}")
            try:
                builds.append(float(fields[1]))
                sweeps.append(float(fields[2]))
            except ValueError as error:
                raise ValueError(f"{path}: traza CIM inválida en la línea {line_number}: {line!r}") from error
    if not builds:
        raise ValueError(f"{path}: la traza CIM no tiene muestras")
    return builds, sweeps


def plot_vs_n(rows: list[dict[str, float | int | str]], output: Path) -> None:
    fig, ax = new_figure()
    plotted_n: list[int] = []
    for source, (color, marker, linestyle, label) in SOURCE_STYLE.items():
        selected = sorted((row for row in rows if row["source"] == source), key=lambda row: int(row["N"]))
        if not selected:
            continue
        ns = [int(row["N"]) for row in selected]
        plotted_n.extend(ns)
        means = [float(row["mean_cim"]) for row in selected]
        bars = [float(row["std_cim"]) for row in selected]
        ax.errorbar(
            ns,
            means,
            yerr=bars,
            marker=marker,
            color=color,
            markeredgecolor="black",
            markeredgewidth=0.6,
            linestyle=linestyle,
            zorder=3,
            label=label,
        )
    style_axes(ax, "cantidad de partículas", "tiempo de búsqueda CIM (s)")
    if plotted_n:
        ax.set_xticks(sorted(set(plotted_n)))
    apply_sci_axis(ax, "y")
    place_legend_below(ax, ncol=1)
    save_figure(fig, output)


def plot_vs_t(trace_dir: Path, output: Path) -> None:
    traces = sorted(trace_dir.glob("tp2_N*_run*.txt"))
    if not traces:
        raise ValueError(f"{trace_dir}: no hay trazas TP2 que coincidan con tp2_N*_run*.txt")

    fig, ax = new_figure()
    for index, path in enumerate(traces):
        builds, sweeps = parse_tp2_trace(path)
        totals = [build + sweep for build, sweep in zip(builds, sweeps)]
        times = list(range(1, len(totals) + 1))
        stem = path.stem
        particle_count = stem.split("_")[1][1:] if "_" in stem else stem
        ax.plot(
            times,
            totals,
            color=SERIES[index % len(SERIES)],
            linewidth=1.4,
            label=rf"$N={particle_count}$",
        )
    style_axes(ax, "tiempo (s)", "tiempo de búsqueda CIM (s)")
    apply_sci_axis(ax, "y")
    place_legend_below(ax, ncol=3)
    save_figure(fig, output)


def print_table(rows: list[dict[str, float | int | str]]) -> None:
    print("\nN  origen   CIM medio [us]   desvio [us]   armado [us]   barrido [us]   ns/particula   rho")
    by_n: dict[int, dict[str, dict[str, float | int | str]]] = {}
    for row in rows:
        by_n.setdefault(int(row["N"]), {})[str(row["source"])] = row
        mean_us = float(row["mean_cim"]) * 1e6
        std_us = float(row["std_cim"]) * 1e6
        build_us = float(row["mean_build"]) * 1e6
        sweep_us = float(row["mean_sweep"]) * 1e6
        per_particle = 1e9 * float(row["mean_cim"]) / int(row["N"])
        print(
            f"{int(row['N']):<4} {row['source']:<7} {mean_us:12.3f} {std_us:10.3f} "
            f"{build_us:11.3f} {sweep_us:11.3f} {per_particle:8.1f}   {float(row['rho']):.3f}"
        )
    print("\nRazón TP2/TP1 (mismo N, tiempo medio de una búsqueda CIM):")
    for n in sorted(by_n):
        if "tp1" in by_n[n] and "tp2" in by_n[n]:
            ratio = float(by_n[n]["tp2"]["mean_cim"]) / float(by_n[n]["tp1"]["mean_cim"])
            print(f"  N={n}: {ratio:.2f}x")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="archivo agregado, por ejemplo data/cim-timing/cim_times.txt")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="ruta de la figura de comparación (por defecto: la del input con extensión .png)",
    )
    parser.add_argument(
        "--traces-dir",
        type=Path,
        default=None,
        help="trazas CIM del TP2; si se indica, también se escribe la figura vs tiempo",
    )
    args = parser.parse_args()

    try:
        rows = read_aggregate(args.input)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    output = args.output or args.input.with_suffix(".png")
    plot_vs_n(rows, output)
    if args.traces_dir is not None:
        try:
            plot_vs_t(args.traces_dir, output.with_name("tiempo_cim_vs_t.png"))
        except (OSError, ValueError) as error:
            parser.error(str(error))
    print_table(rows)


if __name__ == "__main__":
    main()
