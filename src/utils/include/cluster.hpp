#pragma once // replaces ifndef + define from C/old C++

#include "neighbors.hpp"
#include <cstddef>
#include <vector>

/**
 * Based on a particle state or states, finds all available clusters based on
 * CIM output. Options:
 *  - use a time based position file, calculates clusters + observable S for
 * each time using the CIM method, outputs to a file
 *  - takes a neighbour list (cim output), calculates clusters + observable
 * S = # nodes on biggest cluster / total number of nodes
 */

using Cluster = std::vector<int>;
using Clusters = std::vector<Cluster>;

// Finds connected components in a CIM neighbour list.
Clusters find_clusters(const NeighborLists &neighbors);

// Fraction of nodes in the biggest cluster.
double cluster_observable_s(const Clusters &clusters);