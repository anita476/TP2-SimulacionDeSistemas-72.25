#!/usr/bin/env python3
"""Run repeated off-lattice simulations for each noise level in a list.

This mirrors `offlatice_experiment_runner.py` but accepts a `--noise-list`
argument and runs the requested number of runs for each noise value.
"""

from __future__ import annotations

import argparse
import statistics
import subprocess
from pathlib import Path


def parse_va_output(output: str, run: int) -> dict[int, float]:
    values: dict[int, float] = {}
    for line_number, line in enumerate(output.splitlines(), 1):
        fields = line.split()
        if not fields or fields[0].startswith("#") or fields == ["t", "va"]:
            continue
        if len(fields) != 2:
            raise ValueError(f"run {run}: invalid VA output at line {line_number}: {line!r}")
        try:
            time = int(fields[0])
            value = float(fields[1])
        except ValueError as error:
            raise ValueError(f"run {run}: invalid VA output at line {line_number}: {line!r}") from error
        values[time] = value
    if not values:
        raise ValueError(f"run {run}: offlattice executable produced no VA values")
    return values


def read_s_values(path: Path, run: int) -> dict[int, float]:
    values: dict[int, float] = {}
    current_time: int | None = None
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.split()
            if not fields:
                continue
            if fields[0] == "t":
                if len(fields) != 2:
                    raise ValueError(f"run {run}: invalid cluster time at line {line_number}: {line!r}")
                try:
                    current_time = int(fields[1])
                except ValueError as error:
                    raise ValueError(f"run {run}: invalid cluster time at line {line_number}: {line!r}") from error
            elif fields[0] == "S":
                if current_time is None or len(fields) != 2:
                    raise ValueError(f"run {run}: invalid cluster S at line {line_number}: {line!r}")
                try:
                    values[current_time] = float(fields[1])
                except ValueError as error:
                    raise ValueError(f"run {run}: invalid cluster S at line {line_number}: {line!r}") from error
    if not values:
        raise ValueError(f"run {run}: cluster executable produced no S values")
    return values

def write_run_series(path: Path, va_values: dict[int, float], s_values: dict[int, float]) -> None:
    """Guarda la serie de una sola corrida, con las dos observables.

    Es lo único que después permite calcular el desvío del escalar entre realizaciones:
    del agregado no se puede recuperar, porque su tercera columna es la dispersión
    instantánea, que incluye la fluctuación temporal de cada corrida.
    """
    if set(va_values) != set(s_values):
        raise ValueError(f"{path}: va y S no comparten los mismos tiempos")
    lines = ["t va s"]
    for time in sorted(va_values):
        lines.append(f"{time} {va_values[time]:.17g} {s_values[time]:.17g}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")



def aggregate(runs: list[dict[int, float]], name: str) -> str:
    times = set(runs[0])
    if any(set(values) != times for values in runs[1:]):
        raise ValueError(f"{name}: runs do not contain the same time points")
    lines = [f"t average_{name} std_{name}"]
    for time in sorted(times):
        samples = [values[time] for values in runs]
        average = statistics.fmean(samples)
        # Desvio muestral (n-1), el mismo estimador con el que utils/sweeps.py arma la
        # barra de error del escalar. Con una sola corrida no hay dispersion que medir.
        deviation = statistics.stdev(samples) if len(samples) > 1 else 0.0
        lines.append(f"{time} {average:.17g} {deviation:.17g}")
    return "\n".join(lines) + "\n"


def read_config(path: Path) -> dict[str, str]:
    """Lee un `config.txt` (`clave=valor`, con `# config` de encabezado)."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator:
            values[key.strip()] = value.strip()
    return values


def merge_noise_lists(previous: str, current: str) -> str:
    """Une dos `noise_list`, sin repetidos y ordenados por valor."""
    values = {float(field) for field in (previous + " " + current).split()}
    return " ".join(f"{value:g}" for value in sorted(values))


def write_top_config(path: Path, config: dict[str, object]) -> None:
    """Escribe el config del barrido, acumulando sobre el que ya estaba
    """
    if path.is_file():
        previous = read_config(path)
        differences = [
            f"{key}: ya estaba {previous[key]!r} y ahora es {value!r}"
            for key, value in ((key, str(value)) for key, value in config.items())
            if key != "noise_list" and key in previous and previous[key] != value
        ]
        if differences:
            raise SystemExit(
                f"{path}: los parámetros no coinciden con los del barrido que ya está en esa "
                "carpeta; usá otro --output-dir\n  " + "\n  ".join(differences)
            )
        if "noise_list" in previous:
            config = dict(config)
            config["noise_list"] = merge_noise_lists(previous["noise_list"], str(config["noise_list"]))

    lines = ["# config"] + [f"{key}={value}" for key, value in sorted(config.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_command(command: list[str], run: int) -> str:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        details = completed.stderr.strip() or "no error output"
        raise RuntimeError(f"run {run} failed with exit code {completed.returncode}: {details}")
    return completed.stdout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offlattice-executable", "--offlatice-executable", default="build/OffLattice-TP2")
    parser.add_argument("--cluster-executable", default="build/Cluster-TP2")
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument(
        "--output-dir",
        "--output-folder",
        required=True,
        help="folder for trajectories and aggregate files",
    )
    parser.add_argument("--model", choices=("vicsek", "voter"), default="vicsek")
    parser.add_argument("-L", type=float, default=10.0)
    parser.add_argument("--rho", type=float, default=2.0)
    parser.add_argument("-N", type=int, default=0)
    parser.add_argument("--noise-list", nargs="+", type=float, required=True, help="list of noise values (eta) to run")
    parser.add_argument("-v", "--speed", type=float, default=0.03)
    parser.add_argument("--rc", type=float, default=1.0)
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--base-seed", type=int, default=1)
    parser.add_argument("--cluster-L", type=float, default=None)
    parser.add_argument("--cluster-rc", type=float, default=None)
    parser.add_argument("--epsilon", type=float, default=None, help="optional analysis epsilon to store in config.txt")
    parser.add_argument("--epochs", type=int, default=None, help="optional analysis epochs to store in config.txt")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # write top-level config for the whole noise experiment
    top_cfg = {
        "model": args.model,
        "L": args.L,
        "rho": args.rho,
        "N": args.N,
        "noise_list": " ".join(str(x) for x in args.noise_list),
        "speed": args.speed,
        "rc": args.rc,
        "steps": args.steps,
        "stride": args.stride,
        "runs": args.runs,
        "base_seed": args.base_seed,
        "cluster_L": args.cluster_L,
        "cluster_rc": args.cluster_rc,
        "epsilon": args.epsilon,
        "epochs": args.epochs,
    }
    write_top_config(output_dir / "config.txt", top_cfg)

    cluster_l = args.L if args.cluster_L is None else args.cluster_L
    cluster_rc = args.rc if args.cluster_rc is None else args.cluster_rc

    for eta in args.noise_list:
        print(f"running noise={eta:g}", flush=True)
        case_dir = output_dir / f"eta{eta:g}"
        trajectory_dir = case_dir / "trajectories"
        cluster_dir = case_dir / "cluster-results"
        trajectory_dir.mkdir(parents=True, exist_ok=True)
        cluster_dir.mkdir(parents=True, exist_ok=True)
        runs_dir = case_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        va_runs: list[dict[int, float]] = []
        s_runs: list[dict[int, float]] = []

        for run in range(args.runs):
            trajectory_path = trajectory_dir / f"run-{run}.txt"
            cluster_path = cluster_dir / f"run-{run}.txt"
            simulation_command = [
                args.offlattice_executable,
                "--model",
                args.model,
                "-L",
                str(args.L),
                "--rho",
                str(args.rho),
                "--eta",
                str(eta),
                "--speed",
                str(args.speed),
                "--rc",
                str(args.rc),
                "--steps",
                str(args.steps),
                "--stride",
                str(args.stride),
                "--seed",
                str(args.base_seed + run),
                "--out",
                str(trajectory_path),
            ]
            if args.N > 0:
                simulation_command.extend(("-N", str(args.N)))

            va_runs.append(parse_va_output(run_command(simulation_command, run), run))

            cluster_command = [
                args.cluster_executable,
                "--in",
                str(trajectory_path),
                "--out",
                str(cluster_path),
                "--L",
                str(cluster_l),
                "--rc",
                str(cluster_rc),
            ]
            run_command(cluster_command, run)
            s_runs.append(read_s_values(cluster_path, run))
            write_run_series(runs_dir / f"run-{run}.txt", va_runs[-1], s_runs[-1])

        va_output = case_dir / "va.txt"
        cluster_output = case_dir / "cluster_s.txt"
        va_output.write_text(aggregate(va_runs, "va"), encoding="utf-8")
        cluster_output.write_text(aggregate(s_runs, "s"), encoding="utf-8")
        # write config for this case_dir
        cfg = {
            "model": args.model,
            "L": args.L,
            "rho": args.rho,
            "N": args.N,
            "eta": eta,
            "speed": args.speed,
            "rc": args.rc,
            "steps": args.steps,
            "stride": args.stride,
            "runs": args.runs,
            "base_seed": args.base_seed,
            "cluster_L": args.cluster_L,
            "cluster_rc": args.cluster_rc,
            "epsilon": args.epsilon,
            "epochs": args.epochs,
        }
        cfg_lines = ["# config"]
        for k, v in sorted(cfg.items()):
            cfg_lines.append(f"{k}={v}")
        (case_dir / "config.txt").write_text("\n".join(cfg_lines) + "\n", encoding="utf-8")
        print(f"wrote {va_output} and {cluster_output} from {args.runs} runs")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
