# Reproducción de Resultados

## Punto b: evolución temporal de $v_a$ y elección del `t*`

```bash
python3 scripts/va_evolution_runner.py \
	--offlattice-executable build/OffLattice-TP2 \
	--output-dir data/va-evolution \
	--models vicsek voter \
	--rho 2 4 8 \
	--eta 0.1 \
	--steps 4000 --runs 10
```

Figuras: `data/va-evolution/va_evolucion_vicsek.png`,
`va_evolucion_voter.png`, y un PNG por caso. Tabla: `stationary.txt`.
La vertical roja es el inicio del estacionario.

En Vicsek $t^*$ cae ~100–150. El votante ordena más lento: a $\rho=2$,
$t^*\approx 720$; a $\rho=4$ y $8$ el promedio entre corridas todavía se
mueve cerca del final de los 4000 pasos, y el desvío del escalar es
grande. El criterio es el mismo; no se adelanta $t^*$ a ojo.

## Punto g: tiempos de ejecución del CIM

Las densidades del TP2 (`ρ = 2, 4, 8` con `L = 10`) dan `N = 200, 400, 800`,
valores que caen en el barrido de `N` del TP1. Se cronometra el CIM de esas
tres simulaciones y se compara, en la misma máquina, con el CIM del TP1 al
mismo `N`.

Compilar los dos TPs en Release (WSL):

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
cmake -S "../TP1-SimulacionDeSistemas-72.25" -B "../TP1-SimulacionDeSistemas-72.25/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "../TP1-SimulacionDeSistemas-72.25/build" -j
```

Medir y graficar:

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

Salida: `data/cim-timing/cim_times.txt`, `tiempo_cim_vs_N.png` y
`tiempo_cim_vs_t.png`. El TP1 se corre con `L=20`, `M=13`, paredes y
`--method cim`, que es lo que se usó en el punto 4 del TP1. Lo que se compara
es el tiempo de una búsqueda (`build + sweep`), no el de un paso completo de
Vicsek. Las figuras del TP1 usaban la columna `seconds` (búsqueda entera, un
poco más que `build + sweep` porque incluye armar las listas de vecinas). A
igual `N`, ρ_TP2 = 4 ρ_TP1.

## Primera Parte: Vicsek

## Segunda Parte:


------------

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