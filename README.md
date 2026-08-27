# TP2 — Autómata Off-Lattice (Vicsek / votante)

Simulación de Sistemas — 72.25 — ITBA

###  Integrantes
* Matías Leporini Kogan
* Camila Lee
* Ana Negre 

## Compilación

Para el programa principal:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
```
Luego para las animaciones y gráficos:

```bash
python3 -m venv .venv
source /path/to/.venv/activate
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

Stdout: `t va`. Con `--out`: bloques `t / N / va / x y vx vy`.

### Evolución de va (punto b)

El escalar de polarización se promedia solo en el estacionario. $t^*$ es el
primer tiempo desde el cual $|v_a(t)-\mu|\le\epsilon$ hasta el final, donde
$\mu$ es la media de $v_a$ desde ese $t^*$ hasta el último paso. `epochs` es
la longitud mínima de ese sufijo. Un transitorio queda fuera de esa banda.

Casos característicos: Vicsek y votante, $\rho=2,4,8$, $\eta=0.1$. $L=10$,
10 corridas, 4000 pasos, $\epsilon=0.08$, `epochs=200`.

```bash
python3 scripts/va_evolution_runner.py \
	--offlattice-executable build/OffLattice-TP2 \
	--output-dir data/va-evolution
```

Salida: una curva por caso (con la vertical en $t^*$), las grillas
`va_evolucion_vicsek.png` y `va_evolucion_voter.png`, y `stationary.txt` con
$t^*$ y el $v_a$ escalar ($t \ge t^*$, media entre corridas). Una sola curva:

```bash
python3 scripts/plot_va.py --input data/va-evolution/vicsek_rho2_eta0.1/va.txt \
	--epsilon 0.08 --epochs 200
```

### Tiempos de CIM (punto g)

Las simulaciones del TP2 con `ρ = 2, 4, 8` y `L = 10` tienen `N = 200, 400, 800`,
en el mismo rango que el barrido de `N` del TP1. `--cim_trace` escribe el tiempo de
armar la grilla y de barrerla en cada paso. El runner corre esas tres simulaciones,
repite el CIM del TP1 con el mismo `N` y `1000` búsquedas, y deja un agregado para
la figura.

```bash
python3 scripts/cim_timing_runner.py \
	--offlattice-executable build/OffLattice-TP2 \
	--output-dir data/cim-timing \
	-N 200 400 800 --steps 1000

python3 scripts/plot_cim_times.py \
	--input data/cim-timing/cim_times.txt \
	--traces-dir data/cim-timing/traces \
	--output data/cim-timing/tiempo_cim_vs_N.png
```

Si el TP1 está compilado en el directorio hermano, el runner lo detecta solo. Si no:

```bash
python3 scripts/cim_timing_runner.py \
	--offlattice-executable build/OffLattice-TP2 \
	--tp1-executable ../TP1-SimulacionDeSistemas-72.25/build/CIM-TP1 \
	--output-dir data/cim-timing
```

La comparación es `build + sweep` de una búsqueda CIM, no el tiempo total de Vicsek.
El TP1 se mide con sus parámetros originales (`L=20`, `r ∈ [0.23, 0.26]`, paredes,
`M=13`, `--method cim`), en la misma máquina. A igual `N` la densidad del TP2 es
cuatro veces la del TP1, porque `L` es la mitad.

Una sola corrida, sin el runner:

```bash
./build/OffLattice-TP2 --model vicsek --rho 2 --eta 0.1 --steps 1000 --cim_trace data/cim_trace.txt
```

El archivo tiene columnas `t build_seconds sweep_seconds`. Al terminar, stderr
imprime el promedio. Cluster-TP2 acepta el mismo `--cim_trace` sobre una trayectoria
ya generada con `--out`.

### Animaciones

```bash
./build/OffLattice-TP2 --model vicsek --rho 2 --eta 0.1 --steps 500 --seed 10 --stride 5 --out data/traj.txt
python scripts/animate_flock.py --traj data/traj.txt --out data/flock.gif -L 10
```

### Cálculo de clusters

```bash
./build/Cluster-TP2 --in data/traj.txt --out data/clusters.txt -L 10 --rc 1
```

La salida contiene, para cada tiempo, la cantidad de clusters, el observable
`S` (tamaño del cluster más grande sobre el total) y los IDs de sus nodos.

### Experimentos repetidos

Para ejecutar varias simulaciones con la misma configuración, calcular el
promedio y la desviación estándar de `va`, y luego hacer lo mismo con `S`:

```bash
python3 scripts/offlatice_experiment_runner.py \
	--runs 20 \
	--offlattice-executable build/OffLattice-TP2 \
	--cluster-executable build/Cluster-TP2 \
	--output-dir data/experiment-output \
	--model vicsek --rho 2 --eta 0.1 --steps 500
```

Cada corrida se guarda como `trajectories/run-N.txt` dentro de `--output-dir`,
y los resultados de clusters dentro de `trajectories/cluster-results/`.
Los archivos agregados `va.txt` y `cluster_s.txt` contienen `t average_va
std_va` y `t average_s std_s`, respectivamente.


## Reproducción de Resultado
> Para ejecutar el paso a paso utilizado para la presentación e informes ver `docs/Steps.md`