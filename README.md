# TP2 — Autómata Off-Lattice (Vicsek / votante)

Simulación de Sistemas — 72.25 — ITBA

## Compilar

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
./build/Vicsek-TP2
```

Núcleo CIM del TP1 (`linked-lists`): `cell_grid`, `linked_cell_grid`, `neighbors`.
Pendiente: dinámica Vicsek/votante, I/O, observables y animación.
