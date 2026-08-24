cmake_minimum_required(VERSION 3.16)

project(Vicsek-TP2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

include(FetchContent)

FetchContent_Declare(
    argparse
    GIT_REPOSITORY https://github.com/p-ranav/argparse.git
    GIT_TAG v3.2
)

FetchContent_MakeAvailable(argparse)

add_executable(OffLattice-TP2
    src/offlattice_main.cpp
    src/utils/neighbors.cpp
    src/utils/flocking.cpp
)

add_executable(Cluster-TP2
    src/cluster_main.cpp
    src/utils/cluster.cpp
    src/utils/neighbors.cpp
)

target_include_directories(OffLattice-TP2 PRIVATE src/utils/include)
target_link_libraries(OffLattice-TP2 PRIVATE argparse)
target_include_directories(Cluster-TP2 PRIVATE src/utils/include)
target_link_libraries(Cluster-TP2 PRIVATE argparse)
