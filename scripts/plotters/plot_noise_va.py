#!/usr/bin/env python3
"""Calcula y grafica el promedio de $v_a$ por ruido (eta) a partir de carpetas por eta.

Espera un directorio con subcarpetas `eta0.1`, `eta0.2`, ... Cada una debe tener
un `va.txt` agregado (el que generan los runners).

Para cada carpeta se busca el tiempo estacionario, se promedia desde ahí hasta
el final, se escribe un resumen y se grafica eta vs $v_a$ con barras de error
(puntos unidos como guía para el ojo).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Optional, Dict

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from plot_va import read_va, scalar_average
from utils.plot_style import BLUE, new_figure, save_figure, style_axes
from utils.stationary import find_stationary


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
    lines.append("# eta avg_va t_stat")
    for eta, avg, tstat in sorted(rows, key=lambda r: r[0]):
        avg_text = "none" if avg is None else f"{avg:.17g}"
        t_text = "none" if tstat is None else str(tstat)
        lines.append(f"{eta:g} {avg_text} {t_text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"se escribió {path}")


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
    parser.add_argument("--input-dir", type=Path, required=True, help="directorio con subcarpetas eta*")
    parser.add_argument("--output", type=Path, default=None, help="ruta de la imagen (por defecto: input_dir/noise_va.png)")
    parser.add_argument("--out-txt", type=Path, default=None, help="ruta del resumen txt (por defecto: input_dir/noise_va.txt)")
    parser.add_argument("--epsilon", type=float, default=None, help="epsilon para find_stationary (pisa el de config)")
    parser.add_argument("--epochs", type=int, default=None, help="longitud mínima del sufijo para find_stationary (pisa el de config)")
    args = parser.parse_args()

    input_dir = args.input_dir
    if not input_dir.is_dir():
        parser.error(f"{input_dir}: no es un directorio")

    out_image = args.output or (input_dir / "noise_va.png")
    out_txt = args.out_txt or (input_dir / "noise_va.txt")

    rows: list[tuple[float, Optional[float], Optional[int]]] = []
    errors: dict[float, float] = {}

    parent_cfg = read_config_file(input_dir / "config.txt")

    for entry in sorted(input_dir.iterdir()):
        if not entry.is_dir():
            continue
        eta = parse_eta_dir_name(entry.name)
        if eta is None:
            continue
        va_path = entry / "va.txt"
        if not va_path.is_file():
            print(f"se omite {entry}: falta va.txt")
            continue
        try:
            times, averages, deviations = read_va(va_path)
        except (OSError, ValueError) as error:
            print(f"se omite {entry}: no se pudo leer va.txt: {error}")
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
            print(f"se omite {entry}: epsilon/epochs inválidos en config: {error}")
            continue
        if epsilon is None or epochs is None:
            print(f"se omite {entry}: falta epsilon o epochs en config o en los argumentos")
            continue

        try:
            tstat = find_stationary(times, averages, epsilon, epochs)
        except ValueError as error:
            print(f"se omite {entry}: parámetros de estacionario inválidos: {error}")
            continue

        if tstat is None:
            avg_va = None
        else:
            try:
                avg_va = scalar_average(times, averages, tstat)
                window_dev = [dev for time, dev in zip(times, deviations) if time >= tstat]
                if window_dev:
                    errors[eta] = sum(window_dev) / len(window_dev)
            except ValueError as error:
                print(f"se omite {entry}: no se pudo calcular el promedio escalar: {error}")
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

    plot_data = [(eta, avg) for eta, avg, _ in rows if avg is not None]
    if not plot_data:
        print("no hay promedios para graficar")
        return
    etas, avgs = zip(*sorted(plot_data))
    yerr = [errors.get(eta, 0.0) for eta in etas]

    fig, ax = new_figure()
    ax.errorbar(
        etas,
        avgs,
        yerr=yerr,
        color=BLUE,
        marker="o",
        markeredgecolor="black",
        markeredgewidth=0.6,
        linestyle="-",
        zorder=3,
    )
    style_axes(ax, "ruido (rad)", "polarización")
    ax.set_ylim(0.0, 1.0)
    ax.margins(x=0.05)
    save_figure(fig, out_image)


if __name__ == "__main__":
    main()
