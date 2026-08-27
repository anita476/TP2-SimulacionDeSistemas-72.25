#!/usr/bin/env python3
"""Curvas características de va(t) y la ventana estacionaria usada para el promedio escalar."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

from utils.plot_style import apply_academic_style, place_legend_below, save_figure
import matplotlib.pyplot as plt

from offlatice_experiment_runner import aggregate, parse_va_output, run_command
from plot_va import plot_va_on_ax, read_va, scalar_average
from utils.stationary import find_stationary


def write_run_va(path: Path, values: dict[int, float]) -> None:
    lines = ["t va"]
    for time in sorted(values):
        lines.append(f"{time} {values[time]:.17g}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_run_va(path: Path) -> dict[int, float]:
    return parse_va_output(path.read_text(encoding="utf-8"), run=0)


def case_name(model: str, rho: float, eta: float) -> str:
    return f"{model}_rho{rho:g}_eta{eta:g}"


def run_case(args: argparse.Namespace, model: str, rho: float, eta: float) -> Path:
    case_dir = Path(args.output_dir) / case_name(model, rho, eta)
    case_dir.mkdir(parents=True, exist_ok=True)
    va_path = case_dir / "va.txt"
    if args.plot_only:
        if not va_path.is_file():
            raise FileNotFoundError(f"{va_path}: no existe; ejecutar sin --plot-only")
        return va_path

    runs: list[dict[int, float]] = []
    runs_dir = case_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    for run in range(args.runs):
        command = [
            args.offlattice_executable,
            "--model", model,
            "-L", str(args.L),
            "--rho", str(rho),
            "--eta", str(eta),
            "--speed", str(args.speed),
            "--rc", str(args.rc),
            "--steps", str(args.steps),
            "--stride", str(args.stride),
            "--seed", str(args.base_seed + run),
        ]
        values = parse_va_output(run_command(command, run), run)
        write_run_va(runs_dir / f"run-{run}.txt", values)
        runs.append(values)
        print(f"  {case_name(model, rho, eta)} corrida {run + 1}/{args.runs}", flush=True)

    va_path.write_text(aggregate(runs, "va"), encoding="utf-8")
    return va_path


def summarize_case(
    va_path: Path, model: str, rho: float, eta: float, epsilon: float, epochs: int
) -> dict[str, object]:
    times, averages, deviations = read_va(va_path)
    stationary_time = find_stationary(times, averages, epsilon, epochs)
    row: dict[str, object] = {
        "model": model,
        "rho": rho,
        "eta": eta,
        "va_path": va_path,
        "times": times,
        "averages": averages,
        "deviations": deviations,
        "t_stat": stationary_time,
        "mean_va": None,
        "std_va": None,
    }
    if stationary_time is None:
        return row
    row["mean_va"] = scalar_average(times, averages, stationary_time)
    run_files = sorted((va_path.parent / "runs").glob("run-*.txt"))
    samples = []
    for run_path in run_files:
        values = read_run_va(run_path)
        window = [values[time] for time in sorted(values) if time >= stationary_time]
        if window:
            samples.append(statistics.fmean(window))
    if len(samples) > 1:
        row["std_va"] = statistics.stdev(samples)
    elif samples:
        row["std_va"] = 0.0
    return row


def plot_single(row: dict[str, object], output: Path) -> None:
    fig, ax = new_figure()
    plot_va_on_ax(
        ax,
        row["times"],
        row["averages"],
        row["deviations"],
        row["t_stat"],
    )
    save_figure(fig, output)


def plot_grid(rows: list[dict[str, object]], model: str, output: Path) -> None:
    selected = [row for row in rows if row["model"] == model]
    if not selected:
        return
    rhos = sorted({float(row["rho"]) for row in selected})
    etas = sorted({float(row["eta"]) for row in selected})
    by_key = {(float(row["rho"]), float(row["eta"])): row for row in selected}
    apply_academic_style()
    fig, axes = plt.subplots(
        len(rhos),
        len(etas),
        figsize=(7.2 * len(etas), 5.2 * len(rhos)),
        sharex=True,
        sharey=True,
        squeeze=False,
        layout="constrained",
    )
    for i, rho in enumerate(rhos):
        for j, eta in enumerate(etas):
            ax = axes[i][j]
            row = by_key[(rho, eta)]
            plot_va_on_ax(
                ax,
                row["times"],
                row["averages"],
                row["deviations"],
                row["t_stat"],
                vline_with_time=False,
                legend=False,
            )
            ax.set_title(
                rf"$\rho={rho:g}\,\mathrm{{m}}^{{-2}}$, $\eta={eta:g}\,\mathrm{{rad}}$",
                pad=10,
            )
            if i < len(rhos) - 1:
                ax.set_xlabel("")
            if j > 0:
                ax.set_ylabel("")
    handles, labels = axes[0][0].get_legend_handles_labels()
    place_legend_below(fig, handles, labels, ncol=3)
    layout = fig.get_layout_engine()
    if layout is not None:
        layout.set(h_pad=0.4, w_pad=0.08, hspace=0.18, wspace=0.06)
    save_figure(fig, output)


def write_summary(path: Path, rows: list[dict[str, object]], epsilon: float, epochs: int) -> None:
    lines = [
        f"# epsilon={epsilon:g} epochs={epochs}",
        "# el promedio escalar de va se toma para todo t >= t_stat",
        "model rho eta t_stat mean_va std_va",
    ]
    for row in rows:
        t_stat = row["t_stat"]
        mean_va = row["mean_va"]
        std_va = row["std_va"]
        t_text = "none" if t_stat is None else str(t_stat)
        mean_text = "none" if mean_va is None else f"{mean_va:.17g}"
        std_text = "none" if std_va is None else f"{std_va:.17g}"
        lines.append(f"{row['model']} {row['rho']:g} {row['eta']:g} {t_text} {mean_text} {std_text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"se escribió {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offlattice-executable", default="build/OffLattice-TP2")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--models", nargs="+", default=["vicsek", "voter"])
    parser.add_argument("--rho", nargs="+", type=float, default=[2.0, 4.0, 8.0])
    parser.add_argument("--eta", nargs="+", type=float, default=[0.1])
    parser.add_argument("-L", type=float, default=10.0)
    parser.add_argument("-v", "--speed", type=float, default=0.03)
    parser.add_argument("--rc", type=float, default=1.0)
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--base-seed", type=int, default=1)
    parser.add_argument("--epsilon", type=float, default=0.08)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--plot-only", action="store_true", help="reutilizar va.txt ya presente en --output-dir")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.runs < 1:
        raise SystemExit("--runs debe ser al menos 1")
    if args.steps < 1 or args.stride < 1:
        raise SystemExit("--steps y --stride deben ser al menos 1")
    invalid = [name for name in args.models if name not in {"vicsek", "voter"}]
    if invalid:
        raise SystemExit(f"--models desconocidos {invalid}; usar vicsek y/o voter")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for model in args.models:
        for rho in args.rho:
            for eta in args.eta:
                print(f"{case_name(model, rho, eta)}", flush=True)
                va_path = run_case(args, model, rho, eta)
                row = summarize_case(va_path, model, rho, eta, args.epsilon, args.epochs)
                plot_single(row, va_path.with_suffix(".png"))
                rows.append(row)

    for model in args.models:
        plot_grid(rows, model, output_dir / f"va_evolucion_{model}.png")
    write_summary(output_dir / "stationary.txt", rows, args.epsilon, args.epochs)

    missing = [f"{row['model']} rho={row['rho']:g} eta={row['eta']:g}" for row in rows if row["t_stat"] is None]
    if missing:
        raise SystemExit("no se encontró estacionario en: " + ", ".join(missing))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
    except SystemExit:
        raise
