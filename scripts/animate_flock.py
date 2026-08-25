"""Animate a flocking trajectory from Vicsek-TP2 --out.

Format per frame:
    t <step>
    N
    va <polarization>
    x y vx vy
    ...
"""

from __future__ import annotations

import argparse
import math
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle

# TP1 palette (visualize.py / animate_cim.py)
BOX_EDGE = "black"
BOX_LW = 1.2
PARTICLE_EDGE = "#9e9e9e"
PARTICLE_FACE = "#d9d9d9"


def read_trajectory(path: str) -> list[tuple[int, np.ndarray]]:
    frames: list[tuple[int, np.ndarray]] = []
    with open(path, encoding="utf-8") as fh:
        while True:
            header = fh.readline()
            if not header:
                break
            parts = header.split()
            if len(parts) != 2 or parts[0] != "t":
                sys.exit(f"{path}: expected 't <step>', got {header!r}")
            t = int(parts[1])

            n_line = fh.readline()
            if not n_line:
                sys.exit(f"{path}: missing N after t={t}")
            n = int(n_line.strip())

            va_line = fh.readline()
            if not va_line:
                sys.exit(f"{path}: missing va after t={t}")
            va_parts = va_line.split()
            if len(va_parts) != 2 or va_parts[0] != "va":
                sys.exit(f"{path}: expected 'va <value>' after t={t}, got {va_line!r}")
            try:
                float(va_parts[1])
            except ValueError:
                sys.exit(f"{path}: invalid va value at t={t}: {va_parts[1]!r}")

            rows = []
            for _ in range(n):
                line = fh.readline()
                if not line:
                    sys.exit(f"{path}: truncated frame t={t}")
                x, y, vx, vy = map(float, line.split())
                rows.append((x, y, vx, vy))
            frames.append((t, np.asarray(rows, dtype=float)))
    if not frames:
        sys.exit(f"{path}: no frames")
    return frames


def setup_axes(ax: plt.Axes, box: float) -> None:
    margin = 0.04 * box
    ax.set_xlim(-margin, box + margin)
    ax.set_ylim(-margin, box + margin)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.add_patch(Rectangle((0, 0), box, box, fill=False, edgecolor=BOX_EDGE, linewidth=BOX_LW, zorder=10))


def main() -> None:
    parser = argparse.ArgumentParser(description="Animate flocking trajectories (arrows by angle)")
    parser.add_argument("--traj", required=True, help="trajectory from Vicsek-TP2 --out")
    parser.add_argument("--out", default="data/flock.gif", help="output GIF path")
    parser.add_argument("-L", type=float, default=10.0, help="box side (axis limits)")
    parser.add_argument("--fps", type=int, default=8, help="GIF frames per second")
    parser.add_argument("--stride", type=int, default=1, help="use every stride-th saved frame")
    args = parser.parse_args()

    if args.stride < 1:
        sys.exit("--stride must be >= 1")

    frames = read_trajectory(args.traj)[:: args.stride]
    arrow_len = 0.1 * args.L
    n_particles = frames[0][1].shape[0]

    fig, ax = plt.subplots(figsize=(8, 8))
    setup_axes(ax, args.L)

    cmap = plt.get_cmap("hsv")
    norm = Normalize(vmin=0.0, vmax=2.0 * math.pi)
    fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, label="angle θ", shrink=0.85)

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
    title = ax.set_title(
        f"N={n_particles}  L={args.L:g}  (contorno periódico)\nt = {frames[0][0]}",
        fontsize=11,
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
        title.set_text(f"N={n_particles}  L={args.L:g}  (contorno periódico)\nt = {t}")
        return dots, q, title

    anim = FuncAnimation(fig, update, frames=len(frames), interval=1000 / max(args.fps, 1), blit=False)
    fig.tight_layout()
    anim.save(args.out, writer=PillowWriter(fps=args.fps))
    plt.close(fig)
    print(f"wrote {args.out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
