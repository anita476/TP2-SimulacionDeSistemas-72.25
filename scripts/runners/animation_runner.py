#!/usr/bin/env python3
"""Genera los casos de animación del punto (a): simulación + GIF + PNG.
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANIMATE_SCRIPT = REPO_ROOT / "scripts" / "animate_flock.py"


@dataclass(frozen=True)
class Case:
    name: str
    model: str
    rho: float
    eta: float


# Cada par comparte todo menos una variable, y los eta son valores que también están en el
# barrido del ruido, así que la animación y la curva hablan del mismo punto.
CASES: tuple[Case, ...] = (
    # ciclo del ruido
    Case("vicsek_rho4_eta0.1", "vicsek", 4.0, 0.1),
    Case("vicsek_rho4_eta5.0", "vicsek", 4.0, 5.0),
    # ciclo de la densidad con los valores bajos de referencia del barrido
    Case("vicsek_rho1_3pi_eta1.0", "vicsek", 1.0 / (3.0 * math.pi), 1.0),
    Case("vicsek_rho1_2pi_eta1.0", "vicsek", 1.0 / (2.0 * math.pi), 1.0),
    Case("vicsek_rho1_pi_eta1.0", "vicsek", 1.0 / math.pi, 1.0),
    Case("vicsek_rho2_eta1.0", "vicsek", 2.0, 1.0),
    Case("vicsek_rho8_eta1.0", "vicsek", 8.0, 1.0),
    # ciclo del votante
    Case("voter_rho4_eta0.1", "voter", 4.0, 0.1),
    Case("voter_rho4_eta5.0", "voter", 4.0, 5.0),
    Case("voter_rho1_3pi_eta1.0", "voter", 1.0 / (3.0 * math.pi), 1.0),
    Case("voter_rho1_2pi_eta1.0", "voter", 1.0 / (2.0 * math.pi), 1.0),
    Case("voter_rho1_pi_eta1.0", "voter", 1.0 / math.pi, 1.0),
    Case("voter_rho2_eta1.0", "voter", 2.0, 1.0),
    Case("voter_rho8_eta1.0", "voter", 8.0, 1.0),
)


def run(command: list[str]) -> None:
    print("$ " + " ".join(command), flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT)
    if result.returncode != 0:
        sys.exit(f"falló: {' '.join(command)}")


def simulate(case: Case, args: argparse.Namespace, traj: Path) -> None:
    run(
        [
            str(args.offlattice_executable),
            "--model",
            case.model,
            "-L",
            f"{args.box_size:g}",
            "--rho",
            f"{case.rho:g}",
            "--eta",
            f"{case.eta:g}",
            "--steps",
            str(args.steps),
            "--seed",
            str(args.seed),
            "--stride",
            str(args.stride),
            "--out",
            str(traj),
        ]
    )


def animate(case: Case, args: argparse.Namespace, traj: Path, output_dir: Path) -> None:
    command = [
        sys.executable,
        str(ANIMATE_SCRIPT),
        "--traj",
        str(traj),
        "--out",
        str(output_dir / f"{case.name}.gif"),
        "--mp4",
        str(output_dir / f"{case.name}.mp4"),
        "-L",
        f"{args.box_size:g}",
        "--fps",
        str(args.fps),
        "--gif-dpi",
        str(args.gif_dpi),
        "--stills",
        str(output_dir / "stills" / case.name),
    ]
    if args.frames_dir is not None:
        command += [
            "--frames",
            str(args.frames_dir),
            "--frames-prefix",
            case.name,
            "--frames-dpi",
            str(args.frames_dpi),
        ]
    if args.no_gif:
        command.append("--no-gif")
    run(command)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera las animaciones del punto (a)")
    parser.add_argument(
        "--offlattice-executable",
        type=Path,
        default=Path("build/OffLattice-TP2"),
        help="ejecutable de la simulación",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/animaciones"))
    parser.add_argument(
        "--frames-dir",
        type=Path,
        default=None,
        help="carpeta para la secuencia numerada de la versión en vivo "
        "(p. ej. presentation/figs/frames); si no se pasa, no se escribe",
    )
    parser.add_argument("-L", "--box-size", type=float, default=10.0)
    parser.add_argument("--steps", type=int, default=3500, help="pasos simulados")
    parser.add_argument(
        "--stride",
        type=int,
        default=10,
        help="guardar un cuadro cada stride pasos (500/2 deja los 251 cuadros que "
        "espera el \\animategraphics de la presentación)",
    )
    parser.add_argument("--seed", type=int, default=10)
    parser.add_argument("--fps", type=int, default=12, help="cuadros por segundo del GIF")
    parser.add_argument("--gif-dpi", type=int, default=100)
    parser.add_argument("--frames-dpi", type=int, default=150)
    parser.add_argument("--no-gif", action="store_true", help="sólo PNG, sin GIF")
    parser.add_argument(
        "--only",
        nargs="+",
        default=None,
        metavar="CASO",
        help="correr sólo estos casos (por nombre)",
    )
    parser.add_argument("--plot-only", action="store_true", help="reusar las trayectorias, sólo re-dibujar")
    args = parser.parse_args()

    known = {case.name: case for case in CASES}
    if args.only is None:
        cases = list(CASES)
    else:
        unknown = [name for name in args.only if name not in known]
        if unknown:
            sys.exit(f"casos desconocidos: {', '.join(unknown)} (hay: {', '.join(known)})")
        cases = [known[name] for name in args.only]

    output_dir = args.output_dir if args.output_dir.is_absolute() else REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    for case in cases:
        traj = output_dir / f"{case.name}.txt"
        if args.plot_only:
            if not traj.is_file():
                sys.exit(f"{traj}: no existe, no se puede usar --plot-only")
        else:
            simulate(case, args, traj)
        animate(case, args, traj, output_dir)


if __name__ == "__main__":
    main()
