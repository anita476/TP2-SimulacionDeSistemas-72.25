#include <iostream>
#include <random>
#include <vector>

#include "neighbors.hpp"

int main()
{
    constexpr double L = 10.0;
    constexpr double rc = 1.0;
    constexpr int N = 200;
    constexpr unsigned seed = 42;

    std::mt19937 rng(seed);
    std::uniform_real_distribution<double> uni(0.0, L);

    std::vector<Particle> particles(N);
    for (Particle& p : particles) {
        p.x = uni(rng);
        p.y = uni(rng);
        p.r = 0.0;
    }

    const int M = cim_max_grid_side(L, rc, max_radius(particles));
    if (M < 3) {
        std::cerr << "error: no valid CIM grid for L=" << L << " rc=" << rc << '\n';
        return 1;
    }

    CimStats stats_vec;
    CimStats stats_ll;
    const NeighborLists neighbors = cim_neighbors(particles, L, rc, M, /*periodic=*/true,
                                                  /*trace=*/nullptr, &stats_vec);
    const NeighborLists neighbors_ll = cim_linked_neighbors(particles, L, rc, M, /*periodic=*/true,
                                                            /*trace=*/nullptr, &stats_ll);

    std::size_t edge_count = 0;
    for (const auto& row : neighbors) edge_count += row.size();
    edge_count /= 2;

    std::size_t edge_count_ll = 0;
    for (const auto& row : neighbors_ll) edge_count_ll += row.size();
    edge_count_ll /= 2;

    const CimStats counters = cim_untimed_stats(particles, L, rc, M, true, false);
    const CimStats counters_ll = cim_untimed_stats(particles, L, rc, M, true, true);

    std::cout << "Vicsek-TP2 CIM smoke test\n"
              << "  N=" << N << " L=" << L << " rc=" << rc << " M=" << M << " PBC=1\n"
              << "  cim:    pairs=" << edge_count
              << " build_s=" << stats_vec.build_seconds
              << " sweep_s=" << stats_vec.sweep_seconds
              << " pair_tests=" << counters.pair_tests << '\n'
              << "  cim-ll: pairs=" << edge_count_ll
              << " build_s=" << stats_ll.build_seconds
              << " sweep_s=" << stats_ll.sweep_seconds
              << " pair_tests=" << counters_ll.pair_tests << '\n';
    return 0;
}
