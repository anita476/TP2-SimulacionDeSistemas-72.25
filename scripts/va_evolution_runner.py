#!/usr/bin/env python3
"""Curvas características de va(t) y la ventana estacionaria usada para el promedio escalar."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

from offlatice_experiment_runner import aggregate, parse_va_output, run_command
from plot_va import plot_va_on_ax, read_va, scalar_average, slice_va
from utils.plot_style import SERIES, new_figure, place_legend_below, save_figure
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


def plot_single(
    row: dict[str, object],
    output: Path,
    t_min: int | None = None,
    t_max: int | None = None,
) -> None:
    times, averages, deviations = slice_va(row["times"], row["averages"], row["deviations"], t_min, t_max)
    fig, ax = new_figure()
    plot_va_on_ax(ax, times, averages, deviations, row["t_stat"])
    save_figure(fig, output)


LINESTYLES = ("-", "--", "-.", ":")


def overlay_zoom_end(rows: list[dict[str, object]]) -> int:
    end = max(int(row["times"][-1]) for row in rows if row["times"])
    stats = [int(row["t_stat"]) for row in rows if row["t_stat"] is not None]
    if not stats:
        return min(end, 800)
    latest = max(stats)
    earliest = min(stats)
    if latest <= end // 4:
        return min(end, max(400, 4 * latest))
    return min(end, max(800, 2 * earliest))


def plot_overlay(
    rows: list[dict[str, object]],
    output: Path,
    t_min: int | None = None,
    t_max: int | None = None,
) -> None:
    if not rows:
        return
    rows = sorted(rows, key=lambda row: float(row["rho"]))
    fig, ax = new_figure()
    x_left = None
    x_right = None
    for index, row in enumerate(rows):
        times, averages, deviations = slice_va(row["times"], row["averages"], row["deviations"], t_min, t_max)
        color = SERIES[index % len(SERIES)]
        plot_va_on_ax(
            ax,
            times,
            averages,
            deviations,
            row["t_stat"],
            color=color,
            vline_color=color,
            linestyle=LINESTYLES[index % len(LINESTYLES)],
            label=rf"$\rho={float(row['rho']):g}\,\mathrm{{m}}^{{-2}}$",
            std_label=None,
            show_vline=False,
            legend=False,
            apply_limits=False,
        )
        x_left = times[0] if x_left is None else min(x_left, times[0])
        x_right = times[-1] if x_right is None else max(x_right, times[-1])
    ax.set_ylim(0.0, 1.05)
    if x_left is not None and x_right is not None:
        ax.set_xlim(x_left, x_right)
    place_legend_below(ax, ncol=min(3, len(rows)))
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
    parser.add_argument("--t-min", "--t_min", type=int, default=None, help="primer tiempo del recorte (inclusive)")
    parser.add_argument("--t-max", "--t_max", type=int, default=None, help="último tiempo del recorte (inclusive); si se omite, el zoom usa 4 t*")
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
    if args.t_min is not None and args.t_max is not None and args.t_min > args.t_max:
        raise SystemExit("--t-min debe ser menor o igual que --t-max")

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
        by_eta: dict[float, list[dict[str, object]]] = {}
        for row in rows:
            if row["model"] == model:
                by_eta.setdefault(float(row["eta"]), []).append(row)
        for eta, group in by_eta.items():
            suffix = "" if len(by_eta) == 1 else f"_eta{eta:g}"
            plot_overlay(group, output_dir / f"va_evolucion_{model}{suffix}.png")
            zoom_max = args.t_max if args.t_max is not None else overlay_zoom_end(group)
            plot_overlay(
                group,
                output_dir / f"va_evolucion_{model}{suffix}_zoom.png",
                t_min=args.t_min,
                t_max=zoom_max,
            )
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
