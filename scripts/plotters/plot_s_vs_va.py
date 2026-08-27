#!/usr/bin/env python3
"""Scatter de la fracción S frente a la polarización V_A en la ventana estacionaria."""

from __future__ import annotations

import argparse
from pathlib import Path


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from plot_s import read_s
from plot_va import read_va
from utils.plot_style import BLUE, new_figure, save_figure, style_axes
from utils.stationary import find_stationary


def read_config_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    cfg: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        cfg[key.strip()] = value.strip()
    return cfg


def resolve_parameters(config_path: Path | None, epsilon: float | None, epochs: int | None) -> tuple[float, int]:
    config = read_config_file(config_path) if config_path is not None else {}
    resolved_epsilon = epsilon if epsilon is not None else (float(config["epsilon"]) if "epsilon" in config else None)
    resolved_epochs = epochs if epochs is not None else (int(config["epochs"]) if "epochs" in config else None)
    if resolved_epsilon is None or resolved_epochs is None:
        raise ValueError("faltan epsilon o epochs en la config o en la línea de comando")
    return resolved_epsilon, resolved_epochs


def select_stationary_times(
    va_times: list[int],
    va_averages: list[float],
    s_times: list[int],
    s_averages: list[float],
    epsilon: float,
    epochs: int,
) -> tuple[int | None, int | None, int | None]:
    va_tstat = find_stationary(va_times, va_averages, epsilon, epochs)
    s_tstat = find_stationary(s_times, s_averages, epsilon, epochs)
    candidates = [t for t in (va_tstat, s_tstat) if t is not None]
    t_stationary_max = max(candidates) if candidates else None
    return va_tstat, s_tstat, t_stationary_max


def build_points(
    va_times: list[int],
    va_averages: list[float],
    s_times: list[int],
    s_averages: list[float],
    t_stationary_max: int,
) -> tuple[list[float], list[float]]:
    va_by_time = {time: average for time, average in zip(va_times, va_averages)}
    s_by_time = {time: average for time, average in zip(s_times, s_averages)}
    common_times = sorted(time for time in va_by_time if time in s_by_time and time >= t_stationary_max)
    if not common_times:
        raise ValueError(f"no hay tiempos con t >= {t_stationary_max} en ambos archivos")
    x = [va_by_time[time] for time in common_times]
    y = [s_by_time[time] for time in common_times]
    return x, y


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, help="directorio del experimento con va.txt y cluster_s.txt")
    parser.add_argument("--va", type=Path, help="ruta a va.txt (opcional si se da --input-dir)")
    parser.add_argument("--s", type=Path, help="ruta a cluster_s.txt (opcional si se da --input-dir)")
    parser.add_argument("--output", type=Path, default=None, help="ruta de salida; por defecto se escribe en la carpeta del experimento")
    parser.add_argument("--epsilon", type=float, default=None, help="pisa epsilon del config.txt")
    parser.add_argument("--epochs", type=int, default=None, help="pisa epochs del config.txt")
    args = parser.parse_args()

    if args.input_dir is None and (args.va is None or args.s is None):
        parser.error("debe indicar --input-dir o bien --va y --s")

    if args.input_dir is not None:
        va_path = args.input_dir / "va.txt"
        s_path = args.input_dir / "cluster_s.txt"
        output_path = args.output or (args.input_dir / "s_vs_va.png")
        config_path = args.input_dir / "config.txt"
    else:
        va_path = args.va
        s_path = args.s
        output_path = args.output or (va_path.parent / "s_vs_va.png")
        config_path = va_path.parent / "config.txt"

    for path, label in ((va_path, "va.txt"), (s_path, "cluster_s.txt")):
        if not path.is_file():
            parser.error(f"{path}: no existe {label}")

    try:
        epsilon, epochs = resolve_parameters(config_path, args.epsilon, args.epochs)
    except ValueError as error:
        parser.error(str(error))

    try:
        va_times, va_averages, _ = read_va(va_path)
        s_times, s_averages, _ = read_s(s_path)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    va_tstat, s_tstat, t_stationary_max = select_stationary_times(va_times, va_averages, s_times, s_averages, epsilon, epochs)
    if t_stationary_max is None:
        raise SystemExit("no se encontró un tiempo estacionario para va ni para s")

    try:
        x, y = build_points(va_times, va_averages, s_times, s_averages, t_stationary_max)
    except ValueError as error:
        parser.error(str(error))

    print(f"tiempo estacionario va: {va_tstat}")
    print(f"tiempo estacionario s: {s_tstat}")
    print(f"t_stationary_max: {t_stationary_max}")

    fig, ax = new_figure()
    ax.scatter(x, y, color=BLUE, s=34, alpha=0.85, zorder=3)
    style_axes(ax, "polarización", "fracción del clúster gigante")

    x_min, x_max = min(x), max(x)
    y_min, y_max = min(y), max(y)
    x_pad = max(0.02, 0.08 * (x_max - x_min if x_max > x_min else 0.1))
    y_pad = max(0.02, 0.08 * (y_max - y_min if y_max > y_min else 0.1))
    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_figure(fig, output_path)


if __name__ == "__main__":
    main()
