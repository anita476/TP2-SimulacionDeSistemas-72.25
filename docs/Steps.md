# Reproducción de Resultados

## Punto b: evolución temporal de $v_a$

Criterio: $t^*$ es el primer tiempo tal que, de ahí hasta el final,
$|v_a(t)-\mu|\le\epsilon$, con $\mu$ la media de $v_a$ desde ese $t^*$ hasta
el último paso. `epochs` es la longitud mínima del sufijo. El escalar se
promedia para $t \ge t^*$. $\epsilon=0.08$ (8 % del rango de $v_a$),
`epochs=200`.

```bash
python3 scripts/va_evolution_runner.py \
	--offlattice-executable build/OffLattice-TP2 \
	--output-dir data/va-evolution \
	--models vicsek voter \
	--rho 2 4 8 \
	--eta 0.1 \
	--steps 4000 --runs 10 \
	--epsilon 0.08 --epochs 200
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
