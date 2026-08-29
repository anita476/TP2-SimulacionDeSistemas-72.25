#!/usr/bin/env python3
"""Punto (e): polarizacion escalar en funcion de la fraccion del cluster mas grande

Un punto = un valor de eta con coordenadas (<S>,<va>) promediadas desde t* (estacionario) hasta el final de la corrida

t* se elige a ojo observando las evoluciones temporales y se usa con --t-stat [t*]
"""


from __future__ import annotations

import argparse
import sys
import statistics

from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from matplotlib.lines import Line2D

from utils.plot_style import BLUE, GREEN, VERMILLION, new_figure, place_legend_below, save_figure, style_axes

# color y marker -> densidad (usamos circulos, triangulos, cuadrados para distintas densidades como lo hacen en el paper de la biblio de FVM)
# relleno y trazo -> modelo (viscek vs. votante)
COLOR_BY_RHO = {2.0: BLUE, 4.0: VERMILLION, 8.0: GREEN}
MARKER_BY_RHO = {2.0: "o", 4.0: "s", 8.0: "D"}
MODEL_LABEL = {"vicsek": "Vicsek", "voter": "votante"}


class Case(NamedTuple):
    """Una serie de la figura: un barrido en ruido con el t* que se elige a ojo"""

    model: str
    rho: float
    directory: Path
    t_stat: int

    @property
    def label(self) -> str:
        return rf"{MODEL_LABEL[self.model]}, $\rho={self.rho:g}$ m$^{{-2}}$"

class Point(NamedTuple):
    """Un punto de la figura: un valor de ruido ya promediado en el estacionario."""

    eta: float
    s: float
    s_err: float
    va: float
    va_err: float
    
def read_config_file(path: Path) -> dict[str, str]:
    config: dict[str, str] = {}
    if not path.is_file():
        return config
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        config[key.strip()] = value.strip()
    return config


def load_case(directory: Path, t_stat: int) -> Case:
    """Arma un Case leyendo el modelo y la densidad del config.txt del barrido
    """
    config = read_config_file(directory / "config.txt")
    try:
        model, rho = config["model"], float(config["rho"])
    except (KeyError, ValueError) as error:
        raise SystemExit(f"{directory}/config.txt: falta model o rho, o son inválidos") from error
    if model not in MODEL_LABEL:
        raise SystemExit(f"{directory}/config.txt: modelo desconocido {model!r}")
    return Case(model, rho, directory, t_stat)

def read_run_series(path: Path) -> tuple[list[int], list[float], list[float]]:
    """Lee las columnas `t va s` de una corrida."""
    times, va_values, s_values = [], [], []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines()[1:], 2):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 3:
            raise ValueError(f"{path}:{number}: se esperaban las columnas t va s")
        times.append(int(fields[0]))
        va_values.append(float(fields[1]))
        s_values.append(float(fields[2]))
    return times, va_values, s_values


def scalars_from_runs(case_dir: Path, t_stat: int) -> tuple[float, float, float, float] | None:
    """(S, S_err, va, va_err) de una carpeta de ruido, o None si no se puede calcular.

    Cada corrida se promedia por separado desde t* hasta el final; el escalar es la media
    de esos números y el error, su desvío. Eso mide cuán reproducible es el escalar, que es
    lo que va en la barra. Promediar en cambio la columna std del agregado mide la
    dispersión instantánea, que incluye la fluctuación temporal y da hasta 4 veces más
    grande en el votante.
    """
    run_files = sorted((case_dir / "runs").glob("run-*.txt"))
    if len(run_files) < 2:
        print(f"se omite {case_dir}: hacen falta al menos 2 corridas en runs/ y hay {len(run_files)}")
        return None

    va_means, s_means = [], []
    for run_file in run_files:
        times, va_values, s_values = read_run_series(run_file)
        window = [(v, s) for t, v, s in zip(times, va_values, s_values) if t >= t_stat]
        if not window:
            print(f"se omite {case_dir}: no hay muestras con t >= {t_stat}")
            return None
        va_means.append(statistics.fmean(v for v, _ in window))
        s_means.append(statistics.fmean(s for _, s in window))

    return (
        statistics.fmean(s_means), statistics.stdev(s_means),
        statistics.fmean(va_means), statistics.stdev(va_means),
    )


def collect_points(case: Case) -> list[Point]:
    """Un Point por cada carpeta eta* del barrido, ordenados por ruido."""
    points: list[Point] = []
    for entry in sorted(case.directory.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("eta"):
            continue
        try:
            eta = float(entry.name[3:])
        except ValueError:
            continue
        try:
            scalars = scalars_from_runs(entry, case.t_stat)
        except (OSError, ValueError) as error:
            print(f"se omite {entry}: {error}")
            continue
        if scalars is not None:
            points.append(Point(eta, *scalars))

    points.sort(key=lambda point: point.eta)
    return points



def write_summary(path: Path, rows: list[tuple[Case, list[Point]]]) -> None:
    """Deja escalares en texto para poder citarlos sin volver a correr el plotter."""
    lines = [
        "# punto (e): cada fila es un punto de la figura va vs S",
        "# los escalares se promedian desde t_stat (elegido a ojo) hasta el final de la corrida",
        "# el error es el desvío entre realizaciones promediado en esa misma ventana",
        "modelo rho eta t_stat S S_err va va_err",
    ]
    for case, points in rows:
        for p in points:
            lines.append(
                f"{case.model} {case.rho:g} {p.eta:g} {case.t_stat} "
                f"{p.s:.6g} {p.s_err:.6g} {p.va:.6g} {p.va_err:.6g}"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"se escribió {path}")
    
    
    
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", dest="input_dirs", action="append", type=Path, required=True,
                        metavar="DIR", help="barrido en ruido de una densidad y un modelo; repetible")
    parser.add_argument("--t-stat", "--t_stat", dest="t_stats", action="append", type=int, required=True,
                        metavar="T", help="inicio del estacionario de ese barrido; uno por --input-dir, o uno solo para todos")
    parser.add_argument("--output", type=Path, default=Path("data/figuras/va_vs_s.png"))
    parser.add_argument("--out-txt", type=Path, default=None,
                        help="resumen txt (por defecto: el del --output con extensión .txt)")
    parser.add_argument("--x", choices=("s", "va"), default="s",
                        help="qué observable va en el eje x; 's' es lo que pide el enunciado")
    parser.add_argument("--log", action="store_true",
                        help="escala logarítmica en el eje de la polarización (guía 2.4.7)")
    parser.add_argument("--s-lim", "--s_lim", type=float, nargs=2, default=None, metavar=("MIN", "MAX"),
                        help="rango del eje de S; por defecto se ajusta a los datos")

    args = parser.parse_args()

    # Los --t-stat se aparean con los --input-dir por posición. Uno solo vale para todos.
    if len(args.t_stats) == 1:
        t_stats = args.t_stats * len(args.input_dirs)
    elif len(args.t_stats) == len(args.input_dirs):
        t_stats = args.t_stats
    else:
        parser.error(f"se dieron {len(args.input_dirs)} --input-dir y {len(args.t_stats)} --t-stat: "
                     "tiene que haber uno por directorio, o uno solo para todos")

    for directory in args.input_dirs:
        if not directory.is_dir():
            parser.error(f"{directory}: no es un directorio")

    cases = [load_case(directory, t_stat) for directory, t_stat in zip(args.input_dirs, t_stats)]
    rows = [(case, collect_points(case)) for case in cases]
    rows = [(case, points) for case, points in rows if points]
    if not rows:
        raise SystemExit("ningún barrido aportó puntos")

    fig, ax = new_figure(width=7.8, height=6.0)
    handles: list[Line2D] = []
    s_en_x = args.x == "s"

    for case, points in rows:
        color = COLOR_BY_RHO.get(case.rho, BLUE)
        filled = case.model == "vicsek"
        dash = "-" if filled else "--"
        style = dict(
            color=color,
            marker=MARKER_BY_RHO.get(case.rho, "o"),
            linestyle=dash,
            markerfacecolor=color if filled else "none",
            markeredgecolor=color,
            markeredgewidth=1.6,
        )
        s, s_err = [p.s for p in points], [p.s_err for p in points]
        va, va_err = [p.va for p in points], [p.va_err for p in points]
        x, xerr, y, yerr = (s, s_err, va, va_err) if s_en_x else (va, va_err, s, s_err)

        # Las barras van finas, translúcidas y por detrás de los símbolos, para no tapar
        # las curvas; heredan el trazo de su serie para distinguir los dos modelos.
        bars = ax.errorbar(x, y, xerr=xerr, yerr=yerr, fmt="none", ecolor=color,
                           elinewidth=0.9, capsize=2.5 if filled else 0, alpha=0.45, zorder=2)
        for collection in bars[2]:
            collection.set_linestyle(dash)
        # Los puntos se unen en orden de eta, que es el parámetro que recorre la curva.
        ax.plot(x, y, zorder=3, **style)
        handles.append(Line2D([], [], label=case.label, **style))

    etiqueta = {"s": "fracción del clúster gigante", "va": "polarización"}
    style_axes(ax, etiqueta[args.x], etiqueta["va" if s_en_x else "s"])

    # S satura en 1: el grado medio de la red de vecinos (rho*pi*rc^2 = 6.3, 12.6 y 25)
    # supera el umbral de percolación continua en 2D (~4.5) en las tres densidades, así que
    # la componente gigante abarca casi todo el sistema y <S> vive en una franja angosta
    # pegada a 1. El rango sale de los datos, con un margen que despega del eje los puntos
    # que caen justo en S = 1.
    if args.s_lim is not None:
        s_lim = tuple(args.s_lim)
    else:
        low = min(p.s - p.s_err for _, points in rows for p in points)
        margin = max(0.004, 0.08 * (1.0 - low))
        s_lim = (low - margin, 1.0 + margin)

    if s_en_x:
        ax.set_xlim(*s_lim)
        if args.log:
            ax.set_yscale("log")
        else:
            ax.set_ylim(0.0, 1.02)
    else:
        ax.set_ylim(*s_lim)
        if args.log:
            ax.set_xscale("log")
        else:
            ax.set_xlim(0.0, 1.02)

    if args.log:
        # style_axes apaga las marcas menores, así que las referencias intermedias van
        # después. En potencias de diez, como pide la guía 1.9.
        eje = ax.yaxis if s_en_x else ax.xaxis
        eje.set_minor_locator(FixedLocator([0.05, 0.2, 0.5]))
        eje.set_minor_formatter(FixedFormatter(
            [r"$5\times10^{-2}$", r"$2\times10^{-1}$", r"$5\times10^{-1}$"]))
        ax.tick_params(axis="y" if s_en_x else "x", which="minor",
                       labelsize=15, length=4, width=1.0)


    place_legend_below(fig, handles, [h.get_label() for h in handles], ncol=2)
    save_figure(fig, args.output)
    write_summary(args.out_txt or args.output.with_suffix(".txt"), rows)


if __name__ == "__main__":
    main()