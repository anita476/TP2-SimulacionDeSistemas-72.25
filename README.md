# TP2 — Autómata Off-Lattice (Vicsek / votante)

72.25 Simulación de Sistemas — ITBA

###  Integrantes
* Matías Leporini Kogan
* Camila Lee
* Ana Negre 

## Compilación

Para el programa principal:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
```

Deja dos binarios: `build/OffLattice-TP2` (el motor) y `build/Cluster-TP2` (calcula clusters sobre una trayectoria ya generada). 

Luego para las animaciones y gráficos:

```bash
python3 -m venv .venv
source /path/to/.venv/bin/activate
pip install -r scripts/requirements.txt
```

## Ejecución

### Algoritmos

```bash
# Vicsek (promedio de vecinos)
./build/OffLattice-TP2 --model vicsek --rho 2 --eta 0.1 --steps 500 --seed 1

# Votante (copia un vecino al azar)
./build/OffLattice-TP2 --model voter --rho 2 --eta 0.1 --steps 500 --seed 1 --out data/traj.txt
```

Defaults (teórica): `L=10`, `v=0.03` (`-v` / `--speed`), `rc=1`, `dt=1`, `--model vicsek`.

Otros flags: `--stride N` (emite un cuadro cada N pasos, default 1), `--out ruta` (trayectoria), `--cim_trace ruta` (tiempos del CIM, punto g), `-N` (pisa a `--rho` si es > 0).

Stdout: `t va`. Con `--out`: bloques `t / N / va / x y vx vy`.


### Animaciones

```bash
./build/OffLattice-TP2 --model vicsek --rho 2 --eta 0.1 --steps 500 --seed 10 --stride 5 --out data/traj.txt
python3 scripts/animate_flock.py --traj data/traj.txt --out data/flock.gif -L 10
```

Cada partícula se dibuja como un vector velocidad con origen en su posición, coloreado según el ángulo.


Otros flags: `--fps` (cuadros por segundo), `--stride` (usa un cuadro guardado cada N), `--no-gif`, `--stills CARPETA` (escribe `t0.png`, `tmid.png`, `tlast.png`), `--frames CARPETA` + `--frames-prefix NOMBRE` (un PNG por cuadro, `NOMBRE_<i>.png`, para el `\animategraphics` de la presentación), `--gif-dpi` / `--frames-dpi` (resolución).

### Cálculo de clusters

```bash
./build/Cluster-TP2 --in data/traj.txt --out data/clusters.txt --L 10 --rc 1
```

La salida contiene, para cada tiempo, la cantidad de clusters, el observable
`S` (tamaño del cluster más grande sobre el total) y los IDs de sus nodos.

### Experimentos con repetición

Para ejecutar varias simulaciones con la misma configuración, calcular el
promedio y la desviación estándar de `va`, y luego hacer lo mismo con `S`:

```bash
python3 scripts/runners/offlatice_experiment_runner.py --runs [int] --offlattice-executable path/to/OffLattice-TP2 --cluster-executable path/to/Cluster-TP2 --output-dir path/to/output_dir --model [vicsek/voter] --rho [float] --eta [float] --steps [int]
```

Cada corrida se guarda como `trajectories/run-N.txt` dentro de `--output-dir`, y los resultados de clusters dentro de `cluster-results/`.
Los archivos agregados `va.txt` y `cluster_s.txt` contienen `t average_va std_va` y `t average_s std_s`, respectivamente.
Adicionalmente, se escribe un archivo `config.txt` con la configuración utilizada en el experimento. 


Se proporciona un script para ejecutar varias simulaciones variando los valores de $\eta$ pero manteniendo el resto de la configuración fija:

```bash
python3 scripts/runners/offlatice_noise_runner.py --runs [int] --offlattice-executable path/to/OffLattice-TP2 --cluster-executable path/to/Cluster-TP2 --output-dir path/to/output_dir --model [vicsek/voter] --rho [float] --steps [int] --noise-list [float[]]
```

## Post-proceso

Los scripts de análisis están en la carpeta `scripts/`, repartidos por función:

| Carpeta | Contenido | 
| --- | --- |
| `scripts/runners/` | lanzan simulaciones repetidas y agregan las corridas |
| `scripts/plotters/` | leen los agregados y dibujan las figuras |
| `scripts/utils/` | estilo de figuras |


## Reproducción de Resultados
> Para ejecutar el paso a paso utilizado para la presentación e informes, junto con ejemplos de la ejecución de los _plotters_, ver `docs/Steps.md`
