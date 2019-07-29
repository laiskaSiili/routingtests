/*
Copyright (c) 2017 Theodoros Chondrogiannis
*/

#include <iostream>
#include <fstream> 
#include <boost/regex.hpp>
#include <boost/algorithm/string.hpp>

#include "model/graph.hpp"
#include "algorithms/kspwlo.hpp"

using namespace std;

int main(int argc, char **argv) {
    string graphFile = "";
    unsigned int k = 0;
    double theta = -1;
    string algo = "";
    RoadNetwork *rN = 0;
    
    NodeID source = 0, target = 100;
           	   	       	   	
   	int opt = -1;
	while ((opt = getopt(argc, argv, "f:S:D:k:s:a:")) != -1) {
		switch(opt) {
			case 'f':
				graphFile = string(optarg);
				break;
			case 'S':
				source = stoi(string(optarg));
				break;
			case 'D':
				target = stoi(string(optarg));
				break;
			case 'k':
				k = stoi(string(optarg));
				break;
			case 's':
				theta = stof(string(optarg));
				break;
			case 'a':
				algo = string(optarg);
				break;
		}
	}
	
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
    
    vector<Path> result;

	if(boost::iequals(algo, "op")) {
    	result = onepass(rN,source,target,k,theta);
    }
    else if(boost::iequals(algo, "mp")) {
    	result = multipass(rN,source,target,k,theta);
    }
    else if(boost::iequals(algo, "opplus")) {
    	result = onepass_plus(rN,source,target,k,theta);
    }
    else if(boost::iequals(algo, "svp")) {
    	result = svp_plus(rN,source,target,k,theta);
    }
    else if(boost::iequals(algo, "esx")) {
    	result = esx(rN,source,target,k,theta);
    }
    
    cout << source << "\t" << target << "\t[" << result[0].length;
    for(unsigned int j = 1;j<result.size();j++) {
    	cout << "," << result[j].length;
    }
    cout << "]" << endl;
    	
    delete rN;
    return 0;
}
