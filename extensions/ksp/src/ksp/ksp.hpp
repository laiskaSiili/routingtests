#pragma once

#include <string>
#include "algorithms/kspwlo.hpp"
using namespace std;

vector< vector<double> > k_shortest_paths(string graphFile, double k, double theta, NodeID source, NodeID target, string algo);