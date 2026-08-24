#include "flocking.hpp"

#include <cmath>
#include <vector>

#include "neighbors.hpp"

namespace {

constexpr double kPi = 3.14159265358979323846;

void apply_move_and_wrap(std::vector<Particle>& particles, const FlockingParams& params,
                         const std::vector<double>& theta_new)
{
    constexpr double dt = 1.0;
    const int n = static_cast<int>(particles.size());
    for (int i = 0; i < n; ++i) {
        Particle& p = particles[static_cast<std::size_t>(i)];
        p.x += params.v * std::cos(p.theta) * dt;
        p.y += params.v * std::sin(p.theta) * dt;
        p.x -= params.L * std::floor(p.x / params.L);
        p.y -= params.L * std::floor(p.y / params.L);
        if (p.x < 0.0) p.x += params.L;
        if (p.y < 0.0) p.y += params.L;
        p.theta = theta_new[static_cast<std::size_t>(i)];
    }
}

}  // namespace

void init_flocking(std::vector<Particle>& particles, double L, std::mt19937& rng)
{
    std::uniform_real_distribution<double> uni_pos(0.0, L);
    std::uniform_real_distribution<double> uni_theta(0.0, 2.0 * kPi);

    for (Particle& p : particles) {
        p.x = uni_pos(rng);
        p.y = uni_pos(rng);
        p.r = 0.0;
        p.theta = uni_theta(rng);
    }
}

void step_vicsek(std::vector<Particle>& particles, const FlockingParams& params, std::mt19937& rng)
{
    const int n = static_cast<int>(particles.size());
    const NeighborLists neighbors =
        cim_neighbors(particles, params.L, params.rc, params.M, /*periodic=*/true);

    std::uniform_real_distribution<double> uni_noise(-0.5 * params.eta, 0.5 * params.eta);
    std::vector<double> theta_new(static_cast<std::size_t>(n));

    for (int i = 0; i < n; ++i) {
        double sx = std::cos(particles[static_cast<std::size_t>(i)].theta);
        double sy = std::sin(particles[static_cast<std::size_t>(i)].theta);
        for (int j : neighbors[static_cast<std::size_t>(i)]) {
            sx += std::cos(particles[static_cast<std::size_t>(j)].theta);
            sy += std::sin(particles[static_cast<std::size_t>(j)].theta);
        }
        /** /N avging not needed since atan2 is agnostic to it **/
        theta_new[static_cast<std::size_t>(i)] = std::atan2(sy, sx) + uni_noise(rng);
    }

    apply_move_and_wrap(particles, params, theta_new);
}

void step_voter(std::vector<Particle>& particles, const FlockingParams& params, std::mt19937& rng)
{
    const int n = static_cast<int>(particles.size());
    const NeighborLists neighbors =
        cim_neighbors(particles, params.L, params.rc, params.M, /*periodic=*/true);

    std::uniform_real_distribution<double> uni_noise(-0.5 * params.eta, 0.5 * params.eta);
    std::vector<double> theta_new(static_cast<std::size_t>(n));

    for (int i = 0; i < n; ++i) {
        const auto& nb = neighbors[static_cast<std::size_t>(i)];
        double base_theta = particles[static_cast<std::size_t>(i)].theta;
        if (!nb.empty()) {
            std::uniform_int_distribution<int> pick(0, static_cast<int>(nb.size()) - 1);
            base_theta = particles[static_cast<std::size_t>(nb[pick(rng)])].theta;
        }
        theta_new[static_cast<std::size_t>(i)] = base_theta + uni_noise(rng);
    }

    apply_move_and_wrap(particles, params, theta_new);
}

double polarization_va(const std::vector<Particle>& particles)
{
    if (particles.empty()) return 0.0;

    double sx = 0.0;
    double sy = 0.0;
    for (const Particle& p : particles) {
        sx += std::cos(p.theta);
        sy += std::sin(p.theta);
    }
    return std::hypot(sx, sy) / static_cast<double>(particles.size());
}
