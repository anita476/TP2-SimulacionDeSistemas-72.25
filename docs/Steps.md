# Reproducción de Resultados

## Punto b: evolución temporal de $v_a$ y elección del umbral del estacionario

**Qué se eligió y por qué**
* $\eta$: 0.1, 1.0, 3.0, 6.0 - uno bajo (ordenado), 2 medios y uno alto (desordenado) [TODO: elegir bien estos etas pero creo que estan bien]
* $\rho$: 2, 4, 8 - para verificar si el criterio usado es aplicable para distintas densidades (solo se usa densidad = 4 para la presentación)
* pasos: 10.000 pues el votante a $\rho=8$ sigue ordenándose hasta ~2500 s
* modelos: los dos en la misma figura pues el punto (f) pide comparar el votante "en las figuras construidas en los puntos (b, c, d y e)"

**Primero: observar**

```bash
python3 scripts/va_evolution_runner.py \
	--offlattice-executable build/OffLattice-TP2 \
	--output-dir data/va-evolution-b \
	--rho 2 4 8 --eta 0.1 1.0 3.0 6.0 \
	--steps 10000 --runs 10
```

![va vs t, rho = 4, sin umbral](../data/va-evolution-b/va_vs_t_rho4_sin_umbral.png)

Las otras dos densidades, para verificar que el criterio sirve igual:

| $\rho = 2$ | $\rho = 8$ |
|---|---|
| ![](../data/va-evolution-b/va_vs_t_rho2_sin_umbral.png) | ![](../data/va-evolution-b/va_vs_t_rho8_sin_umbral.png) |

Otros archivos que deja en `data/va-evolution-b/`:

- `<modelo>_rho<ρ>_eta<η>/va.txt`: `t average_va std_va` entre las 10 corridas (sirve para este grafico, se puede prender el std con `--std` pero se apaga por default para que se vea mejor)
- `<modelo>_rho<ρ>_eta<η>/runs/run-N.txt`: la serie de cada corrida por separado (sirve para calcular barra de error del escalar luego y para poder re-analizar sin re-simular todo)
[TODO: el "auto" despues habria que sacarlo maybe?]
- `stationary.txt`: `T`, `t_stat`, su origen (`ojo`/`auto`) y el escalar, acumulado entre corridas (sirve para comparar el algoritmo que fijamos antes)

**Segundo: marcar $t^*$**

Es **un solo umbral para todos los $\eta$**: las curvas de ruido alto y bajo son la evidencia de que ese tiempo deja afuera todos los transitorios.

El caso mas importante que manda es **el votante a $\rho=8$ con $\eta=0.1$**, que sigue subiendo hasta cerca de los 2500 s. El umbral es **uno solo para todos los $\eta$ y para los dos modelos**(? TODO: VERIFICAR).

Se elige $t^* = 3000$ s, es decir $0.3\,T$: deja ese transitorio afuera con margen y conserva el 70% de los pasos para promediar.

```bash
python3 scripts/va_evolution_runner.py \
    --output-dir data/va-evolution-b --plot-only \
    --rho 2 4 8 --eta 0.1 1.0 3.0 6.0 --t-stat 3000
```

`--plot-only` reusa los `va.txt` y sólo redibuja, sin volver a simular. La figura que va a la presentación:

![va vs t, rho = 4, con el umbral marcado](../data/va-evolution-b/va_vs_t_rho4.png)

Las otras dos densidades, para verificar que el mismo $t^*$ deja afuera el transitorio
también ahí. No van a la diapositiva; alcanza con decir que se verificó.

| $\rho = 2$ | $\rho = 8$ |
|---|---|
| ![](../data/va-evolution-b/va_vs_t_rho2.png) | ![](../data/va-evolution-b/va_vs_t_rho8.png) |

Además, una figura por modelo de cada densidad (`va_vs_t_rho<ρ>_vicsek.png` y `va_vs_t_rho<ρ>_voter.png`). La que
pide el punto (f) es la comparada.

## Punto c: $<v_a>$ en función del ruido



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