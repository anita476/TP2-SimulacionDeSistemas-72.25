# TP2 — Autómata Off-Lattice (Vicsek / votante)

Simulación de Sistemas — 72.25 — ITBA

## Compilar

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
```

## Correr

```bash
# Vicsek (promedio de vecinos)
./build/Vicsek-TP2 --model vicsek --rho 2 --eta 0.1 --steps 500 --seed 1

# Votante (copia un vecino al azar)
./build/Vicsek-TP2 --model voter --rho 2 --eta 0.1 --steps 500 --seed 1 --out data/traj.txt
```

Defaults (teórica): `L=10`, `v=0.03` (`-v` / `--speed`), `rc=1`, `dt=1`, `--model vicsek`.

Stdout: `t va`. Con `--out`: bloques `t / N / x y vx vy`.

## Animar

```bash
./build/Vicsek-TP2 --model vicsek --rho 2 --eta 0.1 --steps 200 --seed 1 --stride 5 --out data/traj.txt
python scripts/animate_flock.py --traj data/traj.txt --out data/flock.gif -L 10
```

`pip install -r scripts/requirements.txt` si falta matplotlib.
