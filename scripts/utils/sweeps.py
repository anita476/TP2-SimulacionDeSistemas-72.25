"""Piezas compartidas por los plotters de barrido en ruido (puntos c, d y e).

Un barrido es una carpeta `<modelo>_rho<ρ>/` con una subcarpeta por ruido (`eta0.1/`,
`eta0.25/`, ...), cada una con `runs/run-N.txt` (columnas `t va s`) y un `config.txt` que
dice qué modelo y qué densidad se corrieron.  Los tres puntos dibujan las mismas seis
series y con la misma convención, así que el armado de las series vive acá y no en cada
plotter.
"""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Callable, NamedTuple

from matplotlib.lines import Line2D
from matplotlib.ticker import FixedFormatter, FixedLocator

from utils.plot_style import (
    BLUE,
    GREEN,
    MODELS,
    VERMILLION,
    new_figure,
    place_legend_below,
    save_figure,
    style_axes,
)
from utils.plot_style import MODEL_LABELS as MODEL_LABEL  # una sola fuente para los dos nombres

# color y marker -> densidad (usamos circulos, cuadrados y rombos para distintas densidades como lo hacen en el paper de la biblio de FVM)
# relleno y trazo -> modelo (vicsek vs. votante)
COLOR_BY_RHO = {2.0: BLUE, 4.0: VERMILLION, 8.0: GREEN}
MARKER_BY_RHO = {2.0: "o", 4.0: "s", 8.0: "D"}


class Case(NamedTuple):
    """Una serie de la figura: un barrido en ruido con el t* que se elige a ojo."""

    model: str
    rho: float
    directory: Path
    t_stat: int

    @property
    def label(self) -> str:
        return rf"{MODEL_LABEL[self.model]}, {self.rho_label}"

    @property
    def rho_label(self) -> str:
        """Sin el modelo: en una figura de un solo modelo, su nombre es constante y la
        corrección pide que los parámetros constantes vayan afuera, no en la leyenda."""
        return rf"$\rho={self.rho:g}$ m$^{{-2}}$"


class Point(NamedTuple):
    """Un punto de la figura: un valor de ruido ya promediado en el estacionario."""

    eta: float
    va: float
    va_err: float
    s: float
    s_err: float


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
    """Arma un Case leyendo el modelo y la densidad del config.txt del barrido."""
    config = read_config_file(directory / "config.txt")
    try:
        model, rho = config["model"], float(config["rho"])
    except (KeyError, ValueError) as error:
        raise SystemExit(f"{directory}/config.txt: falta model o rho, o son inválidos") from error
    if model not in MODEL_LABEL:
        raise SystemExit(f"{directory}/config.txt: modelo desconocido {model!r}")
    return Case(model, rho, directory, t_stat)


def sort_cases(cases: list[Case]) -> list[Case]:
    """Vicsek antes que el votante y densidad creciente.

    Es el orden en que se llena la leyenda: con `ncol=2` deja una columna por modelo.
    """
    return sorted(cases, key=lambda case: (MODELS.index(case.model), case.rho))


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
    """(va, va_err, S, S_err) de una carpeta de ruido, o None si no se puede calcular.

    Cada corrida se promedia por separado desde t* hasta el final; el escalar es la media
    de esos números y el error, su desvío. Eso mide cuán reproducible es el escalar, que es
    lo que va en la barra.
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
        statistics.fmean(va_means), statistics.stdev(va_means),
        statistics.fmean(s_means), statistics.stdev(s_means),
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


def eta_dirs(case: Case) -> list[tuple[float, Path]]:
    """(eta, carpeta) de cada ruido del barrido, ordenados por ruido."""
    encontrados: list[tuple[float, Path]] = []
    for entry in sorted(case.directory.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("eta"):
            continue
        try:
            encontrados.append((float(entry.name[3:]), entry))
        except ValueError:
            continue
    encontrados.sort()
    return encontrados


def read_aggregate(path: Path, name: str) -> tuple[list[int], list[float], list[float]]:
    """Lee `t average_<name> std_<name>`, el agregado entre corridas que dejan los runners.

    Sirve para la forma de la curva; para el escalar y su error se usan las corridas
    sueltas de `runs/` (ver scalars_from_runs).
    """
    times, averages, deviations = [], [], []
    lineas = path.read_text(encoding="utf-8").splitlines()
    esperado = ["t", f"average_{name}", f"std_{name}"]
    if not lineas or lineas[0].split() != esperado:
        raise ValueError(f"{path}: se esperaban las columnas {' '.join(esperado)}")
    for number, line in enumerate(lineas[1:], 2):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 3:
            raise ValueError(f"{path}:{number}: se esperaban tres columnas")
        times.append(int(fields[0]))
        averages.append(float(fields[1]))
        deviations.append(float(fields[2]))
    if not times:
        raise ValueError(f"{path}: no hay filas de datos")
    return times, averages, deviations


def series_style(case: Case) -> dict[str, object]:
    """Color y símbolo por densidad, relleno y trazo por modelo."""
    color = COLOR_BY_RHO.get(case.rho, BLUE)
    filled = case.model == "vicsek"
    return dict(
        color=color,
        marker=MARKER_BY_RHO.get(case.rho, "o"),
        linestyle="-" if filled else (0, (1.8, 1.8)),
        markerfacecolor=color if filled else "none",
        markeredgecolor=color,
        markeredgewidth=1.6,
    )


Filas = list[tuple[Case, list[Point]]]


def plot_scalar_vs_eta(
    rows: Filas,
    output: Path,
    *,
    ylabel: str,
    value: Callable[[Point], float],
    error: Callable[[Point], float],
    ylim: tuple[float, float] | None = None,
    log: bool = False,
) -> None:
    """Escalar en función del ruido: una serie por (modelo, densidad), con barras.

    `ylim` en None ajusta el eje a los datos, que es lo que hace falta cuando el
    observable vive en una franja angosta (el caso de S, pegado a 1).
    """
    fig, ax = new_figure(width=7.8, height=6.0)
    handles: list[Line2D] = []
    un_solo_modelo = len({case.model for case, _ in rows}) == 1

    for case, points in rows:
        style = series_style(case)
        ax.errorbar(
            [point.eta for point in points],
            [value(point) for point in points],
            yerr=[error(point) for point in points],
            ecolor=style["color"], elinewidth=1.1, capsize=3.0, zorder=3, **style,
        )
        handles.append(
            Line2D([], [], label=case.rho_label if un_solo_modelo else case.label, **style)
        )

    style_axes(ax, "ruido (rad)", ylabel)
    ax.set_xlim(0.0, None)
    ax.margins(x=0.05)
    if log:
        ax.set_yscale("log")
        # style_axes apaga las marcas menores, así que las referencias intermedias van
        # después. En potencias de diez, como pide la guía 1.9.
        ax.yaxis.set_minor_locator(FixedLocator([0.05, 0.2, 0.5]))
        ax.yaxis.set_minor_formatter(FixedFormatter(
            [r"$5\times10^{-2}$", r"$2\times10^{-1}$", r"$5\times10^{-1}$"]))
        ax.tick_params(axis="y", which="minor", labelsize=15, length=4, width=1.0)
    elif ylim is not None:
        ax.set_ylim(*ylim)
    else:
        low = min(value(point) - error(point) for _, points in rows for point in points)
        high = max(value(point) + error(point) for _, points in rows for point in points)
        margin = max(0.004, 0.08 * (high - low))
        ax.set_ylim(low - margin, min(1.0, high) + margin)

    if un_solo_modelo:
        orden, ncol = handles, len(handles)
    else:
        mitad = len(handles) // 2
        orden = [h for par in zip(handles[:mitad], handles[mitad:]) for h in par]
        ncol = mitad
    place_legend_below(fig, orden, [h.get_label() for h in orden], ncol=ncol)
    save_figure(fig, output)


def write_eta_summary(
    path: Path,
    rows: Filas,
    header: list[str],
    columns: str,
    fields: Callable[[Point], tuple[float, ...]],
) -> None:
    """Deja los escalares en texto para poder citarlos sin volver a correr el plotter."""
    lines = list(header) + [columns]
    for case, points in rows:
        for point in points:
            valores = " ".join(f"{v:.6g}" for v in fields(point))
            lines.append(f"{case.model} {case.rho:g} {point.eta:g} {case.t_stat} {valores}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"se escribió {path}")


def pair_t_stats(parser, input_dirs: list[Path], t_stats: list[int]) -> list[int]:
    """Los --t-stat se aparean con los --input-dir por posición; uno solo vale para todos."""
    if len(t_stats) == 1:
        return t_stats * len(input_dirs)
    if len(t_stats) == len(input_dirs):
        return t_stats
    parser.error(
        f"se dieron {len(input_dirs)} --input-dir y {len(t_stats)} --t-stat: "
        "tiene que haber uno por directorio, o uno solo para todos"
    )
