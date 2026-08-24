#include "cluster.hpp"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include <argparse/argparse.hpp>

namespace {

bool read_frame(std::istream &input, int &time,
                std::vector<Particle> &particles) {
  std::string header;
  if (!std::getline(input, header))
    return false;
  if (header.size() < 3 || header.compare(0, 2, "t ") != 0)
    throw std::runtime_error("expected frame header 't <time>'");

  try {
    time = std::stoi(header.substr(2));
  } catch (const std::exception &) {
    throw std::runtime_error("invalid frame time in header: " + header);
  }

  int count = 0;
  if (!(input >> count) || count < 0)
    throw std::runtime_error("expected a non-negative particle count after t=" +
                             std::to_string(time));

  particles.resize(static_cast<std::size_t>(count));
  for (Particle &particle : particles) {
    double vx = 0.0;
    double vy = 0.0;
    if (!(input >> particle.x >> particle.y >> vx >> vy))
      throw std::runtime_error("incomplete particle data in frame t=" +
                               std::to_string(time));
    particle.r = 0.0;
    particle.theta = std::atan2(vy, vx);
  }
  input.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
  return true;
}

} // namespace

int main(int argc, char *argv[]) {
  argparse::ArgumentParser program("Cluster-TP2", "0.1",
                                   argparse::default_arguments::help);
  program.add_argument("--in").required().help("trajectory input path");
  program.add_argument("--out").required().help("cluster output path");
  program.add_argument("--L").default_value(10.0).scan<'g', double>().help(
      "box side length");
  program.add_argument("--rc").default_value(1.0).scan<'g', double>().help(
      "interaction radius");

  try {
    program.parse_args(argc, argv);
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n' << program;
    return 1;
  }

  const std::string input_path = program.get<std::string>("--in");
  const std::string output_path = program.get<std::string>("--out");
  const double box_side = program.get<double>("-L");
  const double cutoff = program.get<double>("--rc");

  if (box_side <= 0.0 || cutoff <= 0.0) {
    std::cerr << "error: --L and --rc must be positive\n";
    return 1;
  }

  std::ifstream input(input_path);
  if (!input) {
    std::cerr << "error: cannot open input path: " << input_path << '\n';
    return 1;
  }

  const std::filesystem::path output(output_path);
  const std::filesystem::path directory = output.parent_path();
  std::error_code directory_error;
  if (!directory.empty() &&
      !std::filesystem::create_directories(directory, directory_error) &&
      directory_error) {
    std::cerr << "error: cannot create output directory: " << directory << ": "
              << directory_error.message() << '\n';
    return 1;
  }

  std::ofstream result(output);
  if (!result) {
    std::cerr << "error: cannot open output path: " << output_path << '\n';
    return 1;
  }

  try {
    int time = 0;
    std::vector<Particle> particles;
    while (read_frame(input, time, particles)) {
      const int grid_side = cim_max_grid_side(box_side, cutoff, 0.0);
      const NeighborLists neighbors = cim_neighbors(
          particles, box_side, cutoff, grid_side, /*periodic=*/true);
      const Clusters clusters = find_clusters(neighbors);

      result << "t " << time << '\n';
      result << "clusters " << clusters.size() << '\n';
      result << "S " << cluster_observable_s(clusters) << '\n';
      for (std::size_t index = 0; index < clusters.size(); ++index) {
        result << "cluster " << index << ' ' << clusters[index].size();
        for (int node : clusters[index])
          result << ' ' << node;
        result << '\n';
      }
    }
  } catch (const std::exception &error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }

  return 0;
}