#!/usr/bin/env python3
"""Punto (b): evoluciones características de va(t) y el umbral del estacionario.

    va_vs_t_rho<ρ>_sin_umbral.png   la pasada de observar, sin vertical
    va_vs_t_rho<ρ>.png              la pasada de marcar, con la vertical en el umbral

El umbral se elige a ojo, en dos pasos:

1. Sin `--t-stat`, la figura sale **sin vertical**: es la que se mira para decidir a
   partir de qué tiempo ninguna curva tiene tendencia.
2. Con `--t-stat`, se rehace con la vertical en el umbral elegido, y el escalar de cada
   configuración se promedia desde ahí.
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path
import sys

_SCRIPTS = Path(__file__).resolve().parent
sys.path[:0] = [str(_SCRIPTS), str(_SCRIPTS / "runners"), str(_SCRIPTS / "plotters")]


from offlatice_experiment_runner import aggregate, parse_va_output, run_command
from plot_va import plot_va_on_ax, read_va, scalar_average, slice_va
from matplotlib.lines import Line2D

from utils.plot_style import (
    EVOLUTION_FONT_SCALE,
    EVOLUTION_LINE_WIDTH,
    EVOLUTION_SIZE,
    EVOLUTION_TSTAR_COLOR,
    MODEL_LABELS,
    MODEL_LINESTYLES,
    MODEL_LINEWIDTHS,
    MODELS,
    SERIES,
    new_figure,
    place_legend_below,
    save_figure,
    scaled_style,
)
from utils.stationary import find_stationary


def parse_t_stat(tokens: list[str] | None, models: list[str]) -> dict[str, int]:
    """`--t-stat 200` o `--t-stat vicsek=150 voter=600`.
    """
    chosen: dict[str, int] = {}
    fallback: int | None = None
    for token in tokens or []:
        name, separator, raw = token.partition("=")
        if not separator:
            name, raw = None, token
        elif name not in MODELS:
            raise SystemExit(f"--t-stat: modelo desconocido {name!r}; usar vicsek y/o voter")
        try:
            value = int(raw)
        except ValueError:
            raise SystemExit(f"--t-stat: {token!r} no es un entero ni modelo=entero")
        if value < 0:
            raise SystemExit("--t-stat no puede ser negativo")
        if name is None:
            if fallback is not None:
                raise SystemExit("--t-stat: sólo se acepta un valor sin modelo")
            fallback = value
        else:
            chosen[name] = value
    if fallback is not None:
        for name in models:
            chosen.setdefault(name, fallback)
    return chosen


def write_run_va(path: Path, values: dict[int, float]) -> None:
    lines = ["t va"]
    for time in sorted(values):
        lines.append(f"{time} {values[time]:.17g}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_run_va(path: Path) -> dict[int, float]:
    return parse_va_output(path.read_text(encoding="utf-8"), run=0)


def case_name(model: str, rho: float, eta: float) -> str:
    return f"{model}_rho{rho:g}_eta{eta:g}"


def run_case(args: argparse.Namespace, model: str, rho: float, eta: float) -> Path:
    case_dir = Path(args.output_dir) / case_name(model, rho, eta)
    va_path = case_dir / "va.txt"
    if args.plot_only:
        if not va_path.is_file():
            raise FileNotFoundError(f"{va_path}: no existe; ejecutar sin --plot-only")
        return va_path

    case_dir.mkdir(parents=True, exist_ok=True)
    runs: list[dict[int, float]] = []
    runs_dir = case_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    for run in range(args.runs):
        command = [
            args.offlattice_executable,
            "--model", model,
            "-L", str(args.L),
            "--rho", str(rho),
            "--eta", str(eta),
            "--speed", str(args.speed),
            "--rc", str(args.rc),
            "--steps", str(args.steps),
            "--stride", str(args.stride),
            "--seed", str(args.base_seed + run),
        ]
        values = parse_va_output(run_command(command, run), run)
        write_run_va(runs_dir / f"run-{run}.txt", values)
        runs.append(values)
        print(f"  {case_name(model, rho, eta)} corrida {run + 1}/{args.runs}", flush=True)

    va_path.write_text(aggregate(runs, "va"), encoding="utf-8")
    return va_path


def summarize_case(
    va_path: Path,
    model: str,
    rho: float,
    eta: float,
    epsilon: float,
    epochs: int,
    forced_t_stat: int | None = None,
) -> dict[str, object]:
    times, averages, deviations = read_va(va_path)
    # TODO: sacar la estimacion automatica pero puede servir para elegir el t* a a ojo
    auto_t_stat = find_stationary(times, averages, epsilon, epochs)
    if forced_t_stat is not None and times and forced_t_stat > times[-1]:
        raise SystemExit(
            f"--t-stat {forced_t_stat} es posterior al último tiempo medido ({times[-1]}) "
            f"en {va_path}"
        )
    stationary_time = auto_t_stat if forced_t_stat is None else forced_t_stat
    row: dict[str, object] = {
        "model": model,
        "rho": rho,
        "eta": eta,
        "va_path": va_path,
        "times": times,
        "averages": averages,
        "deviations": deviations,
        "T": times[-1] if times else 0,
        "t_stat": stationary_time,
        "t_stat_auto": auto_t_stat,
        "chosen": forced_t_stat is not None,
        "mean_va": None,
        "std_va": None,
    }
    if stationary_time is None:
        return row
    row["mean_va"] = scalar_average(times, averages, stationary_time)
    run_files = sorted((va_path.parent / "runs").glob("run-*.txt"))
    samples = []
    for run_path in run_files:
        values = read_run_va(run_path)
        window = [values[time] for time in sorted(values) if time >= stationary_time]
        if window:
            samples.append(statistics.fmean(window))
    if len(samples) > 1:
        row["std_va"] = statistics.stdev(samples)
    elif samples:
        row["std_va"] = 0.0
    return row


def plot_single(
    row: dict[str, object],
    output: Path,
    t_min: int | None = None,
    t_max: int | None = None,
) -> None:
    times, averages, deviations = slice_va(row["times"], row["averages"], row["deviations"], t_min, t_max)
    fig, ax = new_figure()
    plot_va_on_ax(ax, times, averages, deviations, row["t_stat"])
    save_figure(fig, output)


def evolution_window(
    rows: list[dict[str, object]], t_min: int | None, t_max: int | None
) -> tuple[int | None, int | None]:
    """Recorte del eje temporal: por defecto la corrida entera
    """
    if t_max is not None:
        return t_min, t_max
    return t_min, max(int(row["times"][-1]) for row in rows if row["times"])


def plot_evolutions(
    rows: list[dict[str, object]],
    output: Path,
    t_min: int | None = None,
    t_max: int | None = None,
    show_std: bool = False,
) -> None:
    """Figura del punto (b): un ρ fijo, varios η, los dos modelos, un solo umbral.
    """
    if not rows:
        return
    etas = sorted({float(row["eta"]) for row in rows})
    rows = sorted(
        rows,
        key=lambda row: (etas.index(float(row["eta"])), MODELS.index(str(row["model"]))),
    )
    thresholds = sorted({int(row["t_stat"]) for row in rows if row["chosen"]})
    t_min, t_max = evolution_window(rows, t_min, t_max)

    with scaled_style(EVOLUTION_FONT_SCALE, line_width=EVOLUTION_LINE_WIDTH):
        fig, ax = new_figure(*EVOLUTION_SIZE)
        x_left = None
        x_right = None
        for row in rows:
            model = str(row["model"])
            eta = float(row["eta"])
            times, averages, deviations = slice_va(
                row["times"], row["averages"], row["deviations"], t_min, t_max
            )
            plot_va_on_ax(
                ax,
                times,
                averages,
                deviations,
                None,
                show_std=show_std,
                color=SERIES[etas.index(eta) % len(SERIES)],
                linestyle=MODEL_LINESTYLES[model],
                linewidth=MODEL_LINEWIDTHS[model],
                label=None,
                std_label=None,
                show_vline=False,
                legend=False,
                apply_limits=False,
            )
            x_left = times[0] if x_left is None else min(x_left, times[0])
            x_right = times[-1] if x_right is None else max(x_right, times[-1])

        for index, threshold in enumerate(thresholds):
            if x_left is not None and not x_left <= threshold <= x_right:
                continue
            ax.axvline(
                threshold,
                color=EVOLUTION_TSTAR_COLOR,
                linewidth=EVOLUTION_LINE_WIDTH * 1.5,
                linestyle=":",
                zorder=4,
                label=rf"inicio del estacionario ($t={threshold}$ s)" if index == 0 else None,
            )

        ax.set_ylim(0.0, 1.02)
        if x_left is not None and x_right is not None:
            ax.set_xlim(x_left, x_right)
        ax.ticklabel_format(axis="x", style="plain")
        fig.get_layout_engine().set(h_pad=0.15)

        modelos = [name for name in MODELS if any(row["model"] == name for row in rows)]
        fila_eta = [
            (Line2D([], [], color=SERIES[index % len(SERIES)], linestyle="-", linewidth=1.7),
             rf"$\eta={eta:g}$")
            for index, eta in enumerate(etas)
        ]
        fila_modelo = [
            (Line2D([], [], color="0.35", linestyle=MODEL_LINESTYLES[name],
                    linewidth=MODEL_LINEWIDTHS[name]),
             MODEL_LABELS[name])
            for name in (modelos if len(modelos) > 1 else [])
        ]
        if thresholds:
            fila_modelo.append(
                (Line2D([], [], color=EVOLUTION_TSTAR_COLOR, linestyle=":",
                        linewidth=EVOLUTION_LINE_WIDTH * 1.5),
                 rf"$t^*={thresholds[0]}$ s")
            )

        # matplotlib llena la leyenda por columnas, así que para que cada fila salga
        # entera hay que emparejar las dos listas e intercalarlas.
        ncol = max(len(fila_eta), len(fila_modelo))
        vacio = (Line2D([], [], linestyle="none"), "")
        fila_eta += [vacio] * (ncol - len(fila_eta))
        fila_modelo += [vacio] * (ncol - len(fila_modelo))
        entradas = [entry for par in zip(fila_eta, fila_modelo) for entry in par]
        place_legend_below(
            fig, [h for h, _ in entradas], [l for _, l in entradas], ncol=ncol
        )
        save_figure(fig, output)


SUMMARY_HEADER = "model rho eta T t_stat origen mean_va std_va"


def read_summary(path: Path) -> dict[tuple[str, str, str], str]:
    """Filas ya escritas, indexadas por (modelo, ρ, η)."""
    if not path.is_file():
        return {}
    previous: dict[tuple[str, str, str], str] = {}
    text = path.read_text(encoding="utf-8")
    if SUMMARY_HEADER not in text:
        return {}  # formato viejo: se descarta en vez de mezclar columnas distintas
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line.startswith("model "):
            continue
        fields = line.split()
        if len(fields) >= 3:
            previous[(fields[0], fields[1], fields[2])] = line
    return previous


def write_summary(path: Path, rows: list[dict[str, object]], epsilon: float, epochs: int) -> None:
    """Acumula las filas nuevas sobre las que ya estaban.
    """
    merged = read_summary(path)
    for row in rows:
        t_stat = row["t_stat"]
        mean_va = row["mean_va"]
        std_va = row["std_va"]
        t_text = "none" if t_stat is None else str(t_stat)
        mean_text = "none" if mean_va is None else f"{mean_va:.17g}"
        std_text = "none" if std_va is None else f"{std_va:.17g}"
        origen = "ojo" if row["chosen"] else "auto"
        key = (str(row["model"]), f"{row['rho']:g}", f"{row['eta']:g}")
        merged[key] = f"{key[0]} {key[1]} {key[2]} {row['T']} {t_text} {origen} {mean_text} {std_text}"

    lines = [
        "# el promedio escalar de va se toma para todo t >= t_stat",
        "# T es el largo de la corrida: el t_stat automático depende de él, el elegido a ojo no",
        "# origen=ojo: t* fijado con --t-stat; origen=auto: estimado por utils/stationary.py",
        f"# la estimación automática usa epsilon={epsilon:g} epochs={epochs}",
        SUMMARY_HEADER,
    ]
    lines.extend(
        merged[key]
        for key in sorted(
            merged,
            key=lambda k: (
                MODELS.index(k[0]) if k[0] in MODELS else len(MODELS),
                float(k[1]),
                float(k[2]),
            ),
        )
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"se escribió {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offlattice-executable", default="build/OffLattice-TP2")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(MODELS),
        help="modelos a superponer en cada figura; el punto (f) pide comparar los dos",
    )
    parser.add_argument(
        "--rho",
        nargs="+",
        type=float,
        default=[4.0],
        help="densidades; para la figura del punto (b) alcanza una, característica",
    )
    parser.add_argument(
        "--eta",
        nargs="+",
        type=float,
        default=[0.1, 3.0, 6.0],
        help=(
            "ruidos característicos; conviene uno bajo, uno cerca de la transición (que "
            "es el de transitorio más largo) y uno alto"
        ),
    )
    parser.add_argument("-L", type=float, default=10.0)
    parser.add_argument("-v", "--speed", type=float, default=0.03)
    parser.add_argument("--rc", type=float, default=1.0)
    parser.add_argument(
        "--steps",
        type=int,
        default=10000,
        help="el votante a ρ=8 tarda ~2500 s en llegar al estacionario; con menos pasos el transitorio se come media corrida",
    )
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--base-seed", type=int, default=1)
    parser.add_argument(
        "--epsilon",
        type=float,
        default=0.08,
        help="criterio: distancia máxima a la media del sufijo desde t* hasta el final",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=200,
        help="criterio: cantidad mínima de muestras desde t* hasta el final",
    )
    parser.add_argument(
        "--t-stat",
        "--t_stat",
        nargs="+",
        default=None,
        metavar="[MODELO=]T",
        help=(
            "t* elegido a ojo, uno por modelo ('vicsek=150 voter=600') o uno solo para "
            "los dos; sin esto la figura sale sin verticales, que es la que se mira "
            "para elegirlo"
        ),
    )
    parser.add_argument("--t-min", "--t_min", type=int, default=None, help="primer tiempo del recorte (inclusive)")
    parser.add_argument(
        "--t-max",
        "--t_max",
        type=int,
        default=None,
        help="último tiempo del recorte (inclusive); si se omite se grafica la corrida entera",
    )
    parser.add_argument(
        "--std",
        action="store_true",
        help="agregar la banda de desvío; con varias curvas superpuestas tapa el patrón, por eso está apagada",
    )
    parser.add_argument("--no-single-plots", action="store_true", help="no generar el va.png de cada caso")
    parser.add_argument("--plot-only", action="store_true", help="reutilizar los va.txt ya presentes en --output-dir")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.runs < 1:
        raise SystemExit("--runs debe ser al menos 1")
    if args.steps < 1 or args.stride < 1:
        raise SystemExit("--steps y --stride deben ser al menos 1")
    invalid = [name for name in args.models if name not in MODELS]
    if invalid:
        raise SystemExit(f"--models desconocidos {invalid}; usar vicsek y/o voter")
    if args.t_min is not None and args.t_max is not None and args.t_min > args.t_max:
        raise SystemExit("--t-min debe ser menor o igual que --t-max")
    chosen_t_stat = parse_t_stat(args.t_stat, args.models)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for model in args.models:
        for rho in args.rho:
            for eta in args.eta:
                print(f"{case_name(model, rho, eta)}", flush=True)
                va_path = run_case(args, model, rho, eta)
                row = summarize_case(
                    va_path, model, rho, eta, args.epsilon, args.epochs,
                    chosen_t_stat.get(model),
                )
                if not args.no_single_plots:
                    plot_single(row, va_path.with_suffix(".png"), args.t_min, args.t_max)
                rows.append(row)

    # Una figura por densidad: adentro varían el ruido y el modelo.  A la diapositiva va
    # sólo la de ρ = 4; las otras dos son la verificación de que el umbral sirve igual.
    groups: dict[float, list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(float(row["rho"]), []).append(row)
    # Las dos pasadas dejan archivos distintos: si compartieran nombre, volver a mirar
    # borraría las figuras ya marcadas.
    suffix = "" if chosen_t_stat else "_sin_umbral"
    for rho, group in sorted(groups.items()):
        plot_evolutions(
            group,
            output_dir / f"va_vs_t_rho{rho:g}{suffix}.png",
            t_min=args.t_min,
            t_max=args.t_max,
            show_std=args.std,
        )
        # Además de la comparada, una por modelo: con ocho curvas encimadas cuesta
        # seguir una sola, y para explicar el comportamiento de cada modelo conviene
        # verlo aparte.  La comparada es la que pide el punto (f), así que las de un
        # solo modelo van a una subcarpeta y no se mezclan con ella.
        if len(args.models) > 1:
            for model in args.models:
                solo = [row for row in group if row["model"] == model]
                plot_evolutions(
                    solo,
                    output_dir / "por-modelo" / f"va_vs_t_rho{rho:g}_{model}{suffix}.png",
                    t_min=args.t_min,
                    t_max=args.t_max,
                    show_std=args.std,
                )

    write_summary(output_dir / "stationary.txt", rows, args.epsilon, args.epochs)

    missing = [
        f"{row['model']} rho={row['rho']:g} eta={row['eta']:g}"
        for row in rows
        if row["t_stat"] is None
    ]
    if missing:
        raise SystemExit("no se encontró estacionario en: " + ", ".join(missing))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
    except SystemExit:
        raise
