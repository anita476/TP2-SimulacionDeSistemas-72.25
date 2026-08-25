#pragma once

#include <random>
#include <vector>

#include "particle.hpp"

struct CimStats;

struct FlockingParams {
  double L;
  double rc;
  double v;
  double eta;
  int M;
};

// Places particles at a random place, with a random angle
void init_flocking(std::vector<Particle> &particles, double L,
                   std::mt19937 &rng);

// A vicsek tick
void step_vicsek(std::vector<Particle> &particles, const FlockingParams &params,
                 std::mt19937 &rng, CimStats *cim_stats = nullptr);

// A voter tick
void step_voter(std::vector<Particle> &particles, const FlockingParams &params,
                std::mt19937 &rng, CimStats *cim_stats = nullptr);

// Measures particle allignment
double polarization_va(const std::vector<Particle> &particles);
