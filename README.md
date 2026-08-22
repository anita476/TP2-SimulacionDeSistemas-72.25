# TP2 — Autómata Off-Lattice (Vicsek / votante)

Simulación de Sistemas — 72.25 — ITBA

## Compilar

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
```

## Correr (modelo estándar)

```bash
./build/Vicsek-TP2 --rho 2 --eta 0.1 --steps 500 --seed 1
./build/Vicsek-TP2 --rho 2 --eta 5 --steps 500 --seed 1 --out data/traj.txt
```

Defaults (teórica): `L=10`, `v=0.03` (`-v` / `--speed`), `rc=1`, `dt=1`.

Stdout: `t va`. Con `--out`: bloques `t / N / x y vx vy`.

Pendiente: modelo votante, clusters, barridos η y animación.
