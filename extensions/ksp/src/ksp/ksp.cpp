/*
Copyright (c) 2017 Theodoros Chondrogiannis
*/

#include <iostream>
#include <fstream> 
#include <boost/regex.hpp>
#include <boost/algorithm/string.hpp>

#include "model/graph.hpp"
#include "algorithms/kspwlo.hpp"

#include "ksp.hpp"

using namespace std;

vector< vector<double> > k_shortest_paths(string graphFile, double k, double theta, NodeID source, NodeID target, string algo) {

	RoadNetwork *rN = 0;
	
	//Input checking	
	if(graphFile == "" ) {
    	cerr << "Wrong arguments. Define graph file correctly." << endl;
    	exit(1);
    }
    
	if(k < 1) {
    	cerr << "Define k between [1,+inf)" << endl;
    	exit(2);
    }
    
    if(theta < 0 || theta > 1) {
    	cerr << "Define theta between [0,1]" << endl;
    	exit(3);
    }
    
    if(source == target) {
    	cerr << "Source and target are the same node" << endl;
    	exit(4);
    }
    
    // Loading road network
    rN = new RoadNetwork(graphFile.c_str());
    
	vector<Path> shortest_paths;

	if(boost::iequals(algo, "op")) {
		shortest_paths = onepass(rN,source,target,k,theta);
    }
    else if(boost::iequals(algo, "mp")) {
		shortest_paths = multipass(rN,source,target,k,theta);
    }
    else if(boost::iequals(algo, "opplus")) {
		shortest_paths = onepass_plus(rN,source,target,k,theta);
    }
    else if(boost::iequals(algo, "svp")) {
		shortest_paths = svp_plus(rN,source,target,k,theta);
    }
    else if(boost::iequals(algo, "esx")) {
		shortest_paths = esx(rN,source,target,k,theta);
    }
    
	// result_vector is a nested vector. The outer vector contains a vector of doubleegers for each path found, whereby the first entry
	// corresponds to the total length of the path and all subsequent doubleegers correspond to the node ids of the path.
	// A path length of 0 indicates, that somewhen during the calculation of said path an overflow error occured and the path calculation is corrupted.
	vector< vector<double> > result_vector(shortest_paths.size());
	for (double j = 0; j < shortest_paths.size(); j++) {
		result_vector[j].push_back(shortest_paths[j].length);
		for (double i = 0; i < shortest_paths[j].nodes.size(); i++) {
			result_vector[j].push_back(shortest_paths[j].nodes[i]);
		}
	}
    	
    delete rN;
    return result_vector;
}
