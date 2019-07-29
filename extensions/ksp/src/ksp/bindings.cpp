#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "ksp.hpp"

namespace py = pybind11;


PYBIND11_MODULE(ksp, m) {
    m.def("k_shortest_paths", &k_shortest_paths);
}