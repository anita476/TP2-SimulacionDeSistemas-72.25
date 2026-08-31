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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from utils.plot_style import FONT_SIZE, SAVE_DPI, apply_academic_style, style_axes
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
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
    style_axes(ax, "posición $x$", "posición $y$")
    ax.grid(False)
    ax.add_patch(Rectangle((0, 0), box, box, fill=False, edgecolor=BOX_EDGE, linewidth=BOX_LW, zorder=10))


def add_angle_colorbar(fig, ax):
    cmap = plt.get_cmap("hsv")
    norm = Normalize(vmin=ANGLE_MIN, vmax=ANGLE_MAX)
    colorbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, shrink=0.82, pad=0.04)
    colorbar.set_label("ángulo de la velocidad")
    colorbar.set_ticks(list(ANGLE_TICKS), labels=list(ANGLE_TICK_LABELS))
    colorbar.minorticks_off()
    colorbar.ax.yaxis.set_major_locator(FixedLocator(list(ANGLE_TICKS)))
    colorbar.ax.set_yticklabels(list(ANGLE_TICK_LABELS))
    colorbar.ax.tick_params(labelsize=FONT_SIZE)
    return cmap, norm


def write_still(fig, path: Path, dpi: int = SAVE_DPI, tight: bool = True) -> None:
    r"""Guarda un cuadro suelto.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if tight:
        fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0.2, facecolor="white")
    else:
        fig.savefig(path, dpi=dpi, facecolor="white")


def render_rgb(fig) -> Image.Image:
    fig.canvas.draw()
    return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())


def write_gif(fig, update, n_frames: int, path: str, fps: int, dpi: int) -> None:
    """Escribe el GIF con una sola paleta para toda la secuencia.
    """
    if n_frames < 1:
        sys.exit("la trayectoria no tiene cuadros: no hay GIF que escribir")
    previous_dpi = fig.get_dpi()
    fig.set_dpi(dpi)  # el tamaño va en pulgadas, así que esto no re-acomoda nada
    try:
        samples = []
        for index in sorted({0, n_frames // 2, n_frames - 1}):
            update(index)
            samples.append(render_rgb(fig))
        width, height = samples[0].size
        montage = Image.new("RGB", (width, height * len(samples)))
        for position, sample in enumerate(samples):
            montage.paste(sample, (0, position * height))
        palette = montage.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

        gif_frames = []
        for index in range(n_frames):
            update(index)
            gif_frames.append(render_rgb(fig).quantize(palette=palette, dither=Image.Dither.NONE))
    finally:
        fig.set_dpi(previous_dpi)

    gif_frames[0].save(
        path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=round(1000 / max(fps, 1)),
        loop=0,
        disposal=1,
    )


def write_mp4(fig, update, n_frames: int, path: str, fps: int, dpi: int) -> None:
    """Escribe un MP4 a partir de los mismos cuadros de la animación."""
    if n_frames < 1:
        sys.exit("la trayectoria no tiene cuadros: no hay MP4 que escribir")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise SystemExit("ffmpeg no está instalado en el sistema; no se puede exportar MP4")

    previous_dpi = fig.get_dpi()
    fig.set_dpi(dpi)
    try:
        with tempfile.TemporaryDirectory(prefix="flock_frames_") as tmpdir:
            tmp_path = Path(tmpdir)
            for index in range(n_frames):
                update(index)
                frame = render_rgb(fig)
                frame.save(tmp_path / f"frame_{index:04d}.png")
            cmd = [
                ffmpeg,
                "-y",
                "-framerate", str(max(fps, 1)),
                "-i", str(tmp_path / "frame_%04d.png"),
                "-pix_fmt", "yuv420p",
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                str(path),
            ]
            subprocess.run(cmd, check=True)
    finally:
        fig.set_dpi(previous_dpi)


def main() -> None:
    parser = argparse.ArgumentParser(description="Anima trayectorias de bandada (vectores según el ángulo)")
    parser.add_argument("--traj", required=True, help="trayectoria generada por OffLattice-TP2 --out")
    parser.add_argument("--out", default="data/flock.gif", help="ruta del GIF de salida")
    parser.add_argument("--mp4", default=None, help="ruta del MP4 de salida (por defecto: junto al GIF con el mismo nombre base)")
    parser.add_argument("-L", type=float, default=10.0, help="lado de la caja (límites de los ejes)")
    parser.add_argument("--fps", type=int, default=8, help="cuadros por segundo de la animación")
    parser.add_argument("--stride", type=int, default=1, help="usar un cuadro guardado cada stride")
    parser.add_argument("--stills", type=Path, default=None, help="carpeta para PNG de t inicial, medio y final")
    parser.add_argument(
        "--frames",
        type=Path,
        default=None,
        help="carpeta para un PNG por cuadro (<prefijo>_<i>.png), para \\animategraphics",
    )
    parser.add_argument(
        "--frames-prefix",
        default=None,
        help="prefijo de los PNG de --frames (por defecto, el nombre de la trayectoria)",
    )
    parser.add_argument("--frames-dpi", type=int, default=150, help="resolución de los PNG de --frames")
    parser.add_argument(
        "--gif-dpi",
        type=int,
        default=100,
        help="resolución del GIF (la de las figuras deja archivos de decenas de MB)",
    )
    parser.add_argument("--no-gif", action="store_true", help="no guardar el GIF")
    args = parser.parse_args()

    if args.stride < 1:
        sys.exit("--stride debe ser >= 1")
    if args.frames_dpi < 1 or args.gif_dpi < 1:
        sys.exit("--frames-dpi y --gif-dpi deben ser >= 1")

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
        rf"$t = {frames[0][0]}$",
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
        time_text.set_text(rf"$t = {t}$")
        return dots, q, time_text


    fig.canvas.draw()
    fig.set_layout_engine("none")

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
            print(f"se escribió {args.stills / name}")

    if args.frames is not None:
        prefix = args.frames_prefix if args.frames_prefix is not None else Path(args.traj).stem
        for index in range(len(frames)):
            update(index)
            write_still(fig, args.frames / f"{prefix}_{index}.png", dpi=args.frames_dpi, tight=False)
        print(f"se escribieron {len(frames)} cuadros en {args.frames}/{prefix}_<i>.png (i = 0..{len(frames) - 1})")

    gif_path = Path(args.out)
    gif_path.parent.mkdir(parents=True, exist_ok=True)
    mp4_path = Path(args.mp4) if args.mp4 is not None else gif_path.with_suffix(".mp4")
    mp4_path.parent.mkdir(parents=True, exist_ok=True)

    if not args.no_gif:
        write_gif(fig, update, len(frames), str(gif_path), args.fps, args.gif_dpi)
        print(f"se escribió {gif_path} ({len(frames)} cuadros)")

    write_mp4(fig, update, len(frames), str(mp4_path), args.fps, args.gif_dpi)
    print(f"se escribió {mp4_path} ({len(frames)} cuadros)")
    plt.close(fig)


if __name__ == "__main__":
    main()
