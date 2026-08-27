#!/usr/bin/env python3
"""Compute and plot average $S$ per noise (eta) from per-eta folders.

Expects an input directory containing folders named like `eta0.1`, `eta0.2`, ...
Each such folder should contain an aggregated `cluster_s.txt` (as produced by the runners).

For each folder the script finds the stationary time using `utils.stationary.find_stationary`,
computes the scalar average from that time to the end, writes a summary text file and
produces a scatter plot of eta vs average $S$ (points only).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Optional, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.stationary import find_stationary
from plot_s import read_s
from plot_va import scalar_average

def parse_eta_dir_name(name: str) -> Optional[float]:
    if not name.startswith("eta"):
        return None
    try:
        return float(name[3:])
    except ValueError:
        return None


def write_summary(path: Path, rows: list[tuple[float, Optional[float], Optional[int]]], config: dict[str, object]) -> None:
    lines = [f"# config"]
    for k, v in sorted(config.items()):
        lines.append(f"# {k}={v}")
    lines.append("# eta avg_s t_stat")
    for eta, avg, tstat in sorted(rows, key=lambda r: r[0]):
        avg_text = "none" if avg is None else f"{avg:.17g}"
        t_text = "none" if tstat is None else str(tstat)
        lines.append(f"{eta:g} {avg_text} {t_text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def read_config_file(path: Path) -> Dict[str, str]:
    cfg: Dict[str, str] = {}
    if not path.is_file():
        return cfg
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip()
    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True, help="directory containing eta* subfolders")
    parser.add_argument("--output", type=Path, default=None, help="output image path (default: input_dir/noise_s.png)")
    parser.add_argument("--out-txt", type=Path, default=None, help="output summary txt (default: input_dir/noise_s.txt)")
    parser.add_argument("--epsilon", type=float, default=None, help="epsilon for find_stationary (overrides config)")
    parser.add_argument("--epochs", type=int, default=None, help="minimum suffix length for find_stationary (overrides config)")
    args = parser.parse_args()

    input_dir = args.input_dir
    if not input_dir.is_dir():
        parser.error(f"{input_dir}: not a directory")

    out_image = args.output or (input_dir / "noise_s.png")
    out_txt = args.out_txt or (input_dir / "noise_s.txt")

    rows: list[tuple[float, Optional[float], Optional[int]]] = []

    parent_cfg = read_config_file(input_dir / "config.txt")

    for entry in sorted(input_dir.iterdir()):
        if not entry.is_dir():
            continue
        eta = parse_eta_dir_name(entry.name)
        if eta is None:
            continue
        va_path = entry / "cluster_s.txt"
        if not va_path.is_file():
            print(f"skipping {entry}: missing cluster_s.txt")
            continue
        try:
            times, averages, deviations = read_s(va_path)
        except (OSError, ValueError) as error:
            print(f"skipping {entry}: failed to read cluster_s.txt: {error}")
            continue

        # determine config for this case: prefer case/config.txt, else parent config
        case_cfg = read_config_file(entry / "config.txt")
        merged_cfg: Dict[str, str] = {}
        merged_cfg.update(parent_cfg)
        merged_cfg.update(case_cfg)

        try:
            epsilon = args.epsilon if args.epsilon is not None else (
                float(merged_cfg["epsilon"]) if "epsilon" in merged_cfg else None
            )
            epochs = args.epochs if args.epochs is not None else (
                int(merged_cfg["epochs"]) if "epochs" in merged_cfg else None
            )
        except (TypeError, ValueError) as error:
            print(f"skipping {entry}: invalid epsilon/epochs in config: {error}")
            continue
        if epsilon is None or epochs is None:
            print(f"skipping {entry}: epsilon or epochs not specified in config or args")
            continue

        try:
            tstat = find_stationary(times, averages, epsilon, epochs)
        except ValueError as error:
            print(f"skipping {entry}: invalid stationary parameters: {error}")
            continue

        if tstat is None:
            avg_va = None
        else:
            try:
                avg_va = scalar_average(times, averages, tstat)
            except ValueError as error:
                print(f"skipping {entry}: could not compute scalar average: {error}")
                avg_va = None

        rows.append((eta, avg_va, tstat))

    # write summary txt with config: prefer parent config file if present
    # convert parent_cfg values to typed values where reasonable
    config_out: Dict[str, object] = {}
    for k, v in parent_cfg.items():
        # try int then float then leave as string
        try:
            config_out[k] = int(v)
            continue
        except Exception:
            pass
        try:
            config_out[k] = float(v)
            continue
        except Exception:
            pass
        config_out[k] = v
    # no CLI overrides for top-level config; values come from config.txt
    # if parent config omitted epsilon/epochs, try to take them from args
    if "epsilon" not in config_out and args.epsilon is not None:
        config_out["epsilon"] = args.epsilon
    if "epochs" not in config_out and args.epochs is not None:
        config_out["epochs"] = args.epochs

    write_summary(out_txt, rows, config_out)

    # prepare data for plotting: exclude None averages
    plot_data = [(eta, avg) for eta, avg, _ in rows if avg is not None]
    if not plot_data:
        print("no averages to plot")
        return
    etas, avgs = zip(*sorted(plot_data))

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(etas, avgs, color="#176b87", s=40)
    ax.set_xlabel(r"$\eta$")
    ax.set_ylabel(r"$\langle S \rangle$")
    ax.set_title(r"Average $\langle S\rangle$ vs $\eta$")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    out_image.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_image, dpi=150)
    plt.close(fig)
    print(f"wrote {out_image}")


if __name__ == "__main__":
    main()
