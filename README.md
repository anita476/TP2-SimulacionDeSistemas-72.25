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
./build/OffLatice-TP2 --model vicsek --rho 2 --eta 0.1 --steps 500 --seed 1

# Votante (copia un vecino al azar)
./build/OffLatice-TP2 --model voter --rho 2 --eta 0.1 --steps 500 --seed 1 --out data/traj.txt
```

Defaults (teórica): `L=10`, `v=0.03` (`-v` / `--speed`), `rc=1`, `dt=1`, `--model vicsek`.

Stdout: `t va`. Con `--out`: bloques `t / N / va / x y vx vy`.

### Tiempos
Para medir el tiempo de CIM puede utilizarse: 

```bash
./build/OffLattice-TP2 --model [vicsek/votante] --rho [int] --eta [float] --steps [int] --stride [int] --out [path]  --cim_trace path/to/cim_out.txt
```
De igual manera puede medirse el tiempo de CIM para el cálculo de clusters: 

```bash
./build/Cluster-TP2 --in [path] --out [path] --L [int] --rc [int] --cim_trace path/to/cim_trace.txt
```

### Animaciones

```bash
./build/OffLattice-TP2 --model vicsek --rho 2 --eta 0.1 --steps 500 --seed 10--stride 5 --out data/traj.txt
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