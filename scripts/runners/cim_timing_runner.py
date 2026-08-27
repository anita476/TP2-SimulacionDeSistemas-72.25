#!/usr/bin/env python3
"""Time CIM searches in TP2 Vicsek runs and, when available, matching TP1 searches."""

from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
from pathlib import Path


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        raise ValueError("no samples")
    average = statistics.fmean(values)
    deviation = statistics.stdev(values) if len(values) > 1 else 0.0
    return average, deviation


def parse_header_field(header: str, name: str) -> str:
    prefix = f"{name}="
    for token in header.split():
        if token.startswith(prefix):
            return token[len(prefix) :]
    raise ValueError(f"missing {name}= in header: {header!r}")


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


def parse_tp1_csv(path: Path, n: int) -> tuple[list[float], list[float], float, int, int]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    matched = [row for row in rows if int(row["N"]) == n]
    if not matched:
        raise ValueError(f"{path}: no TP1 rows for N={n}")
    builds = [float(row["build_seconds"]) for row in matched]
    sweeps = [float(row["sweep_seconds"]) for row in matched]
    box = float(matched[0]["L"])
    grid = int(matched[0]["M"])
    periodic = int(matched[0]["periodic"])
    return builds, sweeps, box, grid, periodic


def run_command(command: list[str], label: str) -> str:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip() or "no error output"
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}: {details}")
    return completed.stdout


def default_tp1_executable() -> Path | None:
    sibling = Path(__file__).resolve().parents[1].parent / "TP1-SimulacionDeSistemas-72.25" / "build"
    for name in ("CIM-TP1", "CIM-TP1.exe"):
        candidate = sibling / name
        if candidate.is_file():
            return candidate
    return None


def write_aggregate(path: Path, rows: list[str]) -> None:
    header = (
        "source N L M rho periodic n_samples "
        "mean_build std_build mean_sweep std_sweep mean_cim std_cim"
    )
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def format_row(
    source: str,
    n: int,
    box: float,
    grid: int,
    periodic: int,
    builds: list[float],
    sweeps: list[float],
) -> str:
    totals = [build + sweep for build, sweep in zip(builds, sweeps)]
    mean_build, std_build = mean_std(builds)
    mean_sweep, std_sweep = mean_std(sweeps)
    mean_cim, std_cim = mean_std(totals)
    rho = n / (box * box)
    return (
        f"{source} {n} {box:.17g} {grid} {rho:.17g} {periodic} {len(totals)} "
        f"{mean_build:.17g} {std_build:.17g} {mean_sweep:.17g} {std_sweep:.17g} "
        f"{mean_cim:.17g} {std_cim:.17g}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offlattice-executable", default="build/OffLattice-TP2")
    parser.add_argument(
        "--tp1-executable",
        default=None,
        help="TP1 CIM binary; omitted uses the sibling TP1 build if present",
    )
    parser.add_argument("--output-dir", required=True, help="folder for traces and the aggregate file")
    parser.add_argument("-N", nargs="+", type=int, default=[200, 400, 800], help="particle counts")
    parser.add_argument("-L", type=float, default=10.0, help="TP2 box side")
    parser.add_argument("--eta", type=float, default=0.1)
    parser.add_argument("-v", "--speed", type=float, default=0.03)
    parser.add_argument("--rc", type=float, default=1.0)
    parser.add_argument("--steps", type=int, default=1000, help="Vicsek steps and TP1 --repeat")
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--model", choices=("vicsek", "voter"), default="vicsek")
    parser.add_argument("--tp1-L", type=float, default=20.0)
    parser.add_argument("--tp1-M", type=int, default=13)
    parser.add_argument("--tp1-method", choices=("cim", "cim-ll"), default="cim")
    parser.add_argument("--tp1-periodic", action="store_true")
    parser.add_argument("--skip-tp1", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")
    if args.steps < 1:
        raise SystemExit("--steps must be at least 1")
    if any(n <= 0 for n in args.N):
        raise SystemExit("-N values must be positive")

    output_dir = Path(args.output_dir)
    trace_dir = output_dir / "traces"
    tp1_tmp = output_dir / "tp1-tmp"
    trace_dir.mkdir(parents=True, exist_ok=True)

    tp1_executable = Path(args.tp1_executable) if args.tp1_executable else default_tp1_executable()
    run_tp1 = not args.skip_tp1 and tp1_executable is not None
    if not args.skip_tp1 and tp1_executable is None:
        print("warning: no TP1 executable found; measuring TP2 only")

    tp1_csv = output_dir / "tp1_raw.csv"
    if run_tp1 and tp1_csv.exists():
        tp1_csv.unlink()

    rows: list[str] = []
    for n in args.N:
        builds: list[float] = []
        sweeps: list[float] = []
        box = args.L
        grid = 0
        for run in range(args.runs):
            trace_path = trace_dir / f"tp2_N{n}_run{run}.txt"
            command = [
                args.offlattice_executable,
                "--model", args.model,
                "-L", str(args.L),
                "-N", str(n),
                "--eta", str(args.eta),
                "--speed", str(args.speed),
                "--rc", str(args.rc),
                "--steps", str(args.steps),
                "--stride", str(args.steps),
                "--seed", str(args.base_seed + run),
                "--cim_trace", str(trace_path),
            ]
            stdout = run_command(command, f"TP2 N={n} run={run}")
            header = next((line for line in stdout.splitlines() if line.startswith("#")), "")
            if not header:
                raise RuntimeError(f"TP2 N={n} run={run}: missing parameter header")
            box = float(parse_header_field(header, "L"))
            grid = int(parse_header_field(header, "M"))
            if int(parse_header_field(header, "N")) != n:
                raise RuntimeError(f"TP2 N={n} run={run}: executable used a different N")
            run_builds, run_sweeps = parse_tp2_trace(trace_path)
            if len(run_builds) != args.steps:
                raise RuntimeError(
                    f"TP2 N={n} run={run}: expected {args.steps} CIM samples, got {len(run_builds)}"
                )
            builds.extend(run_builds)
            sweeps.extend(run_sweeps)
        rows.append(format_row("tp2", n, box, grid, 1, builds, sweeps))
        print(f"TP2 N={n} listo ({len(builds)} búsquedas CIM)", flush=True)

        if not run_tp1:
            continue

        tp1_tmp.mkdir(parents=True, exist_ok=True)
        tp1_command = [
            str(tp1_executable),
            "-N", str(n),
            "-L", str(args.tp1_L),
            "-M", str(args.tp1_M),
            "--rc", str(args.rc),
            "--method", args.tp1_method,
            "--seed", str(args.base_seed),
            "--repeat", str(args.steps),
            "--csv", str(tp1_csv),
            "--tag", f"N{n}",
            "--static-out", str(tp1_tmp / "static.txt"),
            "--dynamic-out", str(tp1_tmp / "dynamic.txt"),
            "--neighbors-out", str(tp1_tmp / "neighbors.txt"),
        ]
        if args.tp1_periodic:
            tp1_command.append("--periodic")
        run_command(tp1_command, f"TP1 N={n}")
        tp1_builds, tp1_sweeps, tp1_box, tp1_grid, tp1_periodic = parse_tp1_csv(tp1_csv, n)
        if len(tp1_builds) != args.steps:
            raise RuntimeError(
                f"TP1 N={n}: expected {args.steps} CIM samples, got {len(tp1_builds)}"
            )
        rows.append(format_row("tp1", n, tp1_box, tp1_grid, tp1_periodic, tp1_builds, tp1_sweeps))
        print(f"TP1 N={n} listo ({len(tp1_builds)} búsquedas CIM)", flush=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate_path = output_dir / "cim_times.txt"
    write_aggregate(aggregate_path, rows)
    print(f"wrote {aggregate_path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
