#pragma once

#include <random>
#include <vector>

#include "particle.hpp"

struct VicsekParams {
    double L;
    double rc;
    double v;
    double eta;
    int M;
};

// Places particles at a random place, with a random angle
void init_vicsek(std::vector<Particle>& particles, double L, std::mt19937& rng);

// A vicsek tick
void step_vicsek(std::vector<Particle>& particles, const VicsekParams& params, std::mt19937& rng);

// Measures particle allignment
double polarization_va(const std::vector<Particle>& particles);
