"""Anima una trayectoria de bandada a partir de OffLattice-TP2 --out.

Formato por cuadro:
    t <paso>
    N
    va <polarización>
    x y vx vy
    ...
"""

from __future__ import annotations

import argparse
import math
import sys

from utils.plot_style import FONT_SIZE, SAVE_DPI, apply_academic_style, style_axes
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle
from matplotlib.ticker import FixedLocator
from pathlib import Path

# TP1 palette (visualize.py / animate_cim.py)
BOX_EDGE = "black"
BOX_LW = 1.2
PARTICLE_EDGE = "#9e9e9e"
PARTICLE_FACE = "#d9d9d9"
ANGLE_MIN = 0.0
ANGLE_MAX = 2.0 * math.pi
ANGLE_TICKS = (0.0, 0.5 * math.pi, math.pi, 1.5 * math.pi, 2.0 * math.pi)
ANGLE_TICK_LABELS = (r"$0$", r"$\pi/2$", r"$\pi$", r"$3\pi/2$", r"$2\pi$")


def read_trajectory(path: str) -> list[tuple[int, np.ndarray]]:
    frames: list[tuple[int, np.ndarray]] = []
    with open(path, encoding="utf-8") as fh:
        while True:
            header = fh.readline()
            if not header:
                break
            parts = header.split()
            if len(parts) != 2 or parts[0] != "t":
                sys.exit(f"{path}: se esperaba 't <paso>', se obtuvo {header!r}")
            t = int(parts[1])

            n_line = fh.readline()
            if not n_line:
                sys.exit(f"{path}: falta N después de t={t}")
            n = int(n_line.strip())

            va_line = fh.readline()
            if not va_line:
                sys.exit(f"{path}: falta va después de t={t}")
            va_parts = va_line.split()
            if len(va_parts) != 2 or va_parts[0] != "va":
                sys.exit(f"{path}: se esperaba 'va <valor>' después de t={t}, se obtuvo {va_line!r}")
            try:
                float(va_parts[1])
            except ValueError:
                sys.exit(f"{path}: valor de va inválido en t={t}: {va_parts[1]!r}")

            rows = []
            for _ in range(n):
                line = fh.readline()
                if not line:
                    sys.exit(f"{path}: cuadro truncado en t={t}")
                x, y, vx, vy = map(float, line.split())
                rows.append((x, y, vx, vy))
            frames.append((t, np.asarray(rows, dtype=float)))
    if not frames:
        sys.exit(f"{path}: no hay cuadros")
    return frames


def setup_axes(ax: plt.Axes, box: float) -> None:
    margin = 0.04 * box
    ax.set_xlim(-margin, box + margin)
    ax.set_ylim(-margin, box + margin)
    ax.set_aspect("equal")
    style_axes(ax, "posición $x$ (m)", "posición $y$ (m)")
    ax.grid(False)
    ax.add_patch(Rectangle((0, 0), box, box, fill=False, edgecolor=BOX_EDGE, linewidth=BOX_LW, zorder=10))


def add_angle_colorbar(fig, ax):
    cmap = plt.get_cmap("hsv")
    norm = Normalize(vmin=ANGLE_MIN, vmax=ANGLE_MAX)
    colorbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, shrink=0.82, pad=0.04)
    colorbar.set_label("ángulo de la velocidad (rad)")
    colorbar.set_ticks(list(ANGLE_TICKS), labels=list(ANGLE_TICK_LABELS))
    colorbar.minorticks_off()
    colorbar.ax.yaxis.set_major_locator(FixedLocator(list(ANGLE_TICKS)))
    colorbar.ax.set_yticklabels(list(ANGLE_TICK_LABELS))
    colorbar.ax.tick_params(labelsize=FONT_SIZE)
    return cmap, norm


def write_still(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=SAVE_DPI, bbox_inches="tight", pad_inches=0.2, facecolor="white")
    print(f"se escribió {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Anima trayectorias de bandada (vectores según el ángulo)")
    parser.add_argument("--traj", required=True, help="trayectoria generada por OffLattice-TP2 --out")
    parser.add_argument("--out", default="data/flock.gif", help="ruta del GIF de salida")
    parser.add_argument("-L", type=float, default=10.0, help="lado de la caja (límites de los ejes)")
    parser.add_argument("--fps", type=int, default=8, help="cuadros por segundo del GIF")
    parser.add_argument("--stride", type=int, default=1, help="usar un cuadro guardado cada stride")
    parser.add_argument("--stills", type=Path, default=None, help="carpeta para PNG de t inicial, medio y final")
    parser.add_argument("--no-gif", action="store_true", help="no guardar el GIF")
    args = parser.parse_args()

    if args.stride < 1:
        sys.exit("--stride debe ser >= 1")

    frames = read_trajectory(args.traj)[:: args.stride]
    arrow_len = 0.1 * args.L

    apply_academic_style()
    fig, ax = plt.subplots(figsize=(7.0, 6.2), layout="constrained")
    setup_axes(ax, args.L)

    cmap, norm = add_angle_colorbar(fig, ax)

    data0 = frames[0][1]
    angles0 = np.arctan2(data0[:, 3], data0[:, 2]) % (2.0 * math.pi)
    ux0 = np.cos(angles0) * arrow_len
    uy0 = np.sin(angles0) * arrow_len

    dots = ax.scatter(
        data0[:, 0],
        data0[:, 1],
        s=18,
        c=angles0,
        cmap=cmap,
        norm=norm,
        edgecolors=PARTICLE_EDGE,
        linewidths=0.4,
        zorder=4,
    )
    q = ax.quiver(
        data0[:, 0],
        data0[:, 1],
        ux0,
        uy0,
        angles0,
        cmap=cmap,
        norm=norm,
        angles="xy",
        scale_units="xy",
        scale=1.0,
        width=0.006,
        headwidth=4.0,
        headlength=5.0,
        headaxislength=4.5,
        pivot="tail",
        zorder=5,
    )
    dots.set_clim(ANGLE_MIN, ANGLE_MAX)
    q.set_clim(ANGLE_MIN, ANGLE_MAX)
    time_text = ax.text(
        0.0,
        1.02,
        rf"$t = {frames[0][0]}$ s",
        transform=ax.transAxes,
        va="bottom",
        ha="left",
        fontsize=FONT_SIZE,
        zorder=12,
    )

    def update(frame_idx: int):
        t, data = frames[frame_idx]
        angles = np.arctan2(data[:, 3], data[:, 2]) % (2.0 * math.pi)
        ux = np.cos(angles) * arrow_len
        uy = np.sin(angles) * arrow_len
        dots.set_offsets(data[:, :2])
        dots.set_array(angles)
        q.set_offsets(data[:, :2])
        q.set_UVC(ux, uy, angles)
        time_text.set_text(rf"$t = {t}$ s")
        return dots, q, time_text

    if args.stills is not None:
        n_frames = len(frames)
        stills = (
            ("t0.png", 0),
            ("tmid.png", n_frames // 2),
            ("tlast.png", n_frames - 1),
        )
        for name, index in stills:
            update(index)
            write_still(fig, args.stills / name)

    if not args.no_gif:
        anim = FuncAnimation(fig, update, frames=len(frames), interval=1000 / max(args.fps, 1), blit=False)
        anim.save(args.out, writer=PillowWriter(fps=args.fps))
        print(f"se escribió {args.out} ({len(frames)} cuadros)")
    plt.close(fig)


if __name__ == "__main__":
    main()
