#!/usr/bin/env python3
"""Plot CIM search times from cim_timing_runner.py."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SOURCE_STYLE = {
    "tp2": ("#176b87", "o"),
    "tp1": ("#d62728", "s"),
}


def source_label(source: str, rows: list[dict[str, float | int | str]]) -> str:
    selected = next((row for row in rows if row["source"] == source), None)
    if selected is None:
        return source
    boundary = "PBC" if int(selected["periodic"]) else "paredes"
    box = float(selected["L"])
    grid = int(selected["M"])
    if source == "tp2":
        return f"TP2 Vicsek (L={box:g}, r=0, {boundary}, M={grid})"
    if source == "tp1":
        return f"TP1 CIM (L={box:g}, r≈0.25, {boundary}, M={grid})"
    return source


def density_note(rows: list[dict[str, float | int | str]]) -> str:
    tp2 = next((row for row in rows if row["source"] == "tp2"), None)
    tp1 = next((row for row in rows if row["source"] == "tp1"), None)
    if tp2 is None or tp1 is None:
        return ""
    ratio = (float(tp1["L"]) / float(tp2["L"])) ** 2
    return (
        f"a igual N, ρ_TP2 = {ratio:g} ρ_TP1 "
        f"(L={float(tp2['L']):g} vs L={float(tp1['L']):g})"
    )


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
            raise ValueError(f"{path}: expected columns {' '.join(sorted(required))}")
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
                raise ValueError(f"{path}: invalid data at line {line_number}") from error
    if not rows:
        raise ValueError(f"{path}: no data rows")
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
                raise ValueError(f"{path}: invalid CIM trace at line {line_number}: {line!r}")
            try:
                builds.append(float(fields[1]))
                sweeps.append(float(fields[2]))
            except ValueError as error:
                raise ValueError(f"{path}: invalid CIM trace at line {line_number}: {line!r}") from error
    if not builds:
        raise ValueError(f"{path}: CIM trace has no samples")
    return builds, sweeps


def plot_vs_n(rows: list[dict[str, float | int | str]], output: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5.5))
    samples = None
    for source, (color, marker) in SOURCE_STYLE.items():
        selected = sorted((row for row in rows if row["source"] == source), key=lambda row: int(row["N"]))
        if not selected:
            continue
        ns = [int(row["N"]) for row in selected]
        means = [float(row["mean_cim"]) * 1e6 for row in selected]
        bars = [
            min(float(row["std_cim"]) * 1e6, mean * 0.95) if mean > 0 else float(row["std_cim"]) * 1e6
            for row, mean in zip(selected, means)
        ]
        samples = int(selected[0]["n_samples"])
        ax.errorbar(
            ns,
            means,
            yerr=bars,
            marker=marker,
            color=color,
            capsize=3,
            markersize=7,
            linewidth=2,
            label=source_label(source, rows),
        )
    ax.set_xlabel("N (cantidad de partículas)")
    ax.set_ylabel("tiempo de CIM por búsqueda [µs]")
    title = "Tiempos de ejecución del CIM: TP2 vs TP1"
    extra = density_note(rows)
    if samples is not None:
        sample_note = f"barra = desvío estándar, {samples} búsquedas"
        extra = f"{extra}; {sample_note}" if extra else sample_note
    if extra:
        title += f"\n{extra}"
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"wrote {output}")


def plot_vs_t(trace_dir: Path, output: Path) -> None:
    traces = sorted(trace_dir.glob("tp2_N*_run*.txt"))
    if not traces:
        raise ValueError(f"{trace_dir}: no TP2 traces matching tp2_N*_run*.txt")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = ["#176b87", "#d62728", "#2a9d8f", "#e9c46a"]
    for index, path in enumerate(traces):
        builds, sweeps = parse_tp2_trace(path)
        totals = [(build + sweep) * 1e6 for build, sweep in zip(builds, sweeps)]
        times = list(range(1, len(totals) + 1))
        stem = path.stem
        particle_count = stem.split("_")[1][1:] if "_" in stem else stem
        label = f"N={particle_count}"
        ax.plot(times, totals, color=colors[index % len(colors)], linewidth=1.2, label=label)
    ax.set_xlabel("t")
    ax.set_ylabel("tiempo de CIM por búsqueda [µs]")
    ax.set_title("Tiempo de CIM por paso en las simulaciones del TP2")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"wrote {output}")


def print_table(rows: list[dict[str, float | int | str]]) -> None:
    print("\nN  source   mean CIM [µs]   std [µs]   build [µs]   sweep [µs]   ns/part   ρ")
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
    parser.add_argument("--input", type=Path, required=True, help="aggregate file, such as data/cim-timing/cim_times.txt")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="comparison figure path (default: input path with a .png suffix)",
    )
    parser.add_argument(
        "--traces-dir",
        type=Path,
        default=None,
        help="TP2 CIM traces; if set, also writes a time-series figure",
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
