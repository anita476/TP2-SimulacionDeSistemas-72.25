#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>

#include <argparse/argparse.hpp>

#include "flocking.hpp"
#include "neighbors.hpp"

namespace {

void write_frame(std::ostream &out, int t, double va,
                 const std::vector<Particle> &particles, double v) {
  out << "t " << t << '\n';
  out << particles.size() << '\n';
  out << "va " << va << '\n';
  for (const Particle &p : particles) {
    const double vx = v * std::cos(p.theta);
    const double vy = v * std::sin(p.theta);
    out << p.x << ' ' << p.y << ' ' << vx << ' ' << vy << '\n';
  }
}

} // namespace

int main(int argc, char *argv[]) {
  argparse::ArgumentParser program("Vicsek-TP2", "0.1",
                                   argparse::default_arguments::help);

  program.add_argument("-L").default_value(10.0).scan<'g', double>().help(
      "box side length");
  program.add_argument("--rho").default_value(2.0).scan<'g', double>().help(
      "density N/L^2");
  program.add_argument("-N").default_value(0).scan<'i', int>().help(
      "particle count (overrides --rho if > 0)");
  program.add_argument("--eta").default_value(0.1).scan<'g', double>().help(
      "noise amplitude");
  program.add_argument("-v", "--speed")
      .default_value(0.03)
      .scan<'g', double>()
      .help("speed magnitude");
  program.add_argument("--rc").default_value(1.0).scan<'g', double>().help(
      "interaction radius");
  program.add_argument("--steps").default_value(500).scan<'i', int>().help(
      "number of time steps");
  program.add_argument("--seed").default_value(1u).scan<'u', unsigned>().help(
      "RNG seed");
  program.add_argument("--stride")
      .default_value(1)
      .scan<'i', int>()
      .help("print/dump every stride steps");
  program.add_argument("--out")
      .default_value(std::string(""))
      .help("trajectory output path");
  program.add_argument("--model")
      .default_value(std::string("vicsek"))
      .help("update rule: vicsek | voter");
  program.add_argument("--cim_trace")
      .default_value(std::string(""))
      .help("CIM timing output path");

  try {
    program.parse_args(argc, argv);
  } catch (const std::exception &err) {
    std::cerr << err.what() << '\n';
    std::cerr << program;
    return 1;
  }

  const double L = program.get<double>("-L");
  const double rho = program.get<double>("--rho");
  int N = program.get<int>("-N");
  const double eta = program.get<double>("--eta");
  const double v = program.get<double>("--speed");
  const double rc = program.get<double>("--rc");
  const int steps = program.get<int>("--steps");
  const unsigned seed = program.get<unsigned>("--seed");
  const int stride = program.get<int>("--stride");
  const std::string out_path = program.get<std::string>("--out");
  const std::string model = program.get<std::string>("--model");
  const std::string cim_trace_path = program.get<std::string>("--cim_trace");

  if (model != "vicsek" && model != "voter") {
    std::cerr << "error: --model must be vicsek or voter\n";
    return 1;
  }
  if (L <= 0.0 || rc <= 0.0 || v < 0.0 || eta < 0.0 || steps < 0 ||
      stride < 1) {
    std::cerr << "error: invalid numeric parameters "
                 "(need L>0, rc>0, v>=0, eta>=0, steps>=0, stride>=1)\n";
    return 1;
  }
  if (N <= 0) {
    if (rho <= 0.0) {
      std::cerr << "error: --rho must be positive when -N is not set\n";
      return 1;
    }
    N = static_cast<int>(std::llround(rho * L * L));
  }
  if (N <= 0) {
    std::cerr << "error: N must be positive (got N=" << N << ")\n";
    return 1;
  }

  const int M = cim_max_grid_side(L, rc, /*r_max=*/0.0);
  if (M < 3) {
    std::cerr << "error: no valid CIM grid for L=" << L << " rc=" << rc
              << " (M=" << M << ")\n";
    return 1;
  }

  std::ofstream cim_trace;
  if (!cim_trace_path.empty()) {
    const std::filesystem::path trace_path(cim_trace_path);
    const std::filesystem::path trace_directory = trace_path.parent_path();
    std::error_code trace_directory_error;
    if (!trace_directory.empty() &&
        !std::filesystem::create_directories(trace_directory,
                                             trace_directory_error) &&
        trace_directory_error) {
      std::cerr << "error: cannot create CIM trace directory: "
                << trace_directory << ": " << trace_directory_error.message()
                << '\n';
      return 1;
    }
    cim_trace.open(trace_path);
    if (!cim_trace) {
      std::cerr << "error: cannot open --cim_trace path: " << cim_trace_path
                << '\n';
      return 1;
    }
    cim_trace << std::setprecision(17);
    cim_trace << "t build_seconds sweep_seconds\n";
  }

  const FlockingParams params{L, rc, v, eta, M};
  CimStats cim_stats;
  const bool use_voter = (model == "voter");

  std::vector<Particle> particles(static_cast<std::size_t>(N));
  std::mt19937 rng(seed);
  init_flocking(particles, L, rng);

  std::ofstream traj;
  if (!out_path.empty()) {
    const std::filesystem::path output_path(out_path);
    const std::filesystem::path output_directory = output_path.parent_path();
    std::error_code directory_error;
    if (!output_directory.empty() &&
        !std::filesystem::create_directories(output_directory,
                                             directory_error) &&
        directory_error) {
      std::cerr << "error: cannot create output directory: " << output_directory
                << ": " << directory_error.message() << '\n';
      return 1;
    }

    traj.open(output_path);
    if (!traj) {
      std::cerr << "error: cannot open --out path: " << out_path << '\n';
      return 1;
    }
  }

  std::cout << "# model=" << model << " L=" << L << " N=" << N
            << " rho=" << (static_cast<double>(N) / (L * L)) << " eta=" << eta
            << " v=" << v << " rc=" << rc << " M=" << M << " steps=" << steps
            << " seed=" << seed << '\n';
  std::cout << "t va\n";

  auto emit = [&](int t) {
    const double va = polarization_va(particles);
    std::cout << t << ' ' << va << '\n';
    if (traj.is_open())
      write_frame(traj, t, va, particles, v);
  };

  emit(0);
  double cim_build_total = 0.0;
  double cim_sweep_total = 0.0;
  for (int t = 1; t <= steps; ++t) {
    if (use_voter)
      step_voter(particles, params, rng, &cim_stats);
    else
      step_vicsek(particles, params, rng, &cim_stats);
    cim_build_total += cim_stats.build_seconds;
    cim_sweep_total += cim_stats.sweep_seconds;
    if (cim_trace.is_open())
      cim_trace << t << ' ' << cim_stats.build_seconds << ' '
                << cim_stats.sweep_seconds << '\n';
    if (t % stride == 0 || t == steps)
      emit(t);
  }

  if (cim_trace.is_open() && steps > 0) {
    const double searches = static_cast<double>(steps);
    std::cerr << std::setprecision(17)
              << "CIM mean " << (cim_build_total + cim_sweep_total) / searches
              << " s over " << steps << " searches | build "
              << cim_build_total / searches << " s | sweep "
              << cim_sweep_total / searches << " s\n";
  }

  return 0;
}
