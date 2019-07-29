/*
Copyright (c) 2017 Theodoros Chondrogiannis
*/

#include "graph.hpp"

RoadNetwork::RoadNetwork(const char *filename) {
    
    FILE *fp;
    NodeID lnode, rnode, tmp;
    double w;
    char c;

    fp = fopen(filename, "r");
    // fscanf(fp, "%c\n", &c);	Mfolini: I guess this first line was doubleended to specify the tdatatype of weights. But as it is hardcoded as double, this is not necessary.
    //fscanf(fp, "%u %u\n", &this->numNodes, &this->numEdges); // Mfolini: Extended this line to accept also a third dummy value to facilitate generating this file by exporting from numpy/pandas.  
	fscanf(fp, "%lf %lf %lf\n", &this->numNodes, &this->numEdges, &tmp);
    this->adjListOut = vector<EdgeList>(this->numNodes);
    this->adjListInc = vector<EdgeList>(this->numNodes);
    
	// Mfolini: Removed 4th dummy value as it does not seem to be used. Now the adjacency list consists of 3 columns (source node, target node, weight).
	/*
	while (fscanf(fp, "%u %u %d %u\n", &lnode, &rnode, &w, &tmp) != EOF) {
        this->adjListOut[lnode].insert(make_pair(rnode, w));
        this->adjListInc[rnode].insert(make_pair(lnode, w));
    }
	*/

    while (fscanf(fp, "%lf %lf %lf\n", &lnode, &rnode, &w) != EOF) {
        this->adjListOut[lnode].insert(make_pair(rnode, w));
        this->adjListInc[rnode].insert(make_pair(lnode, w));
    }
    fclose(fp);
}

double RoadNetwork::getEdgeWeight(NodeID lnode, NodeID rnode) {
    return this->adjListOut[lnode][rnode];
}

RoadNetwork::~RoadNetwork() {
    this->adjListOut.clear();
   	this->adjListInc.clear();
}

bool operator==(const Edge& le, const Edge& re) {
    return (le.first == re.first && le.second == re.second) || (le.second == re.first && le.first == re.second);
}

bool Path::containsEdge(Edge e) {
    bool res = false;
    
	for(double i=0;i<this->nodes.size()-1;i++) {
		if(this->nodes[i] == e.first && this->nodes[i+1] == e.second) {
			res = true;
			break;
		}
	}
	
    return res;
}

double Path::overlap_ratio(RoadNetwork *rN, Path &path2) {
	double sharedLength = 0;
	
	for(double i=0;i<path2.nodes.size()-1;i++) {
		Edge e = make_pair(path2.nodes[i],path2.nodes[i+1]);
		if(this->containsEdge(e))
			sharedLength += rN->getEdgeWeight(path2.nodes[i],path2.nodes[i+1]);
	}

    return sharedLength/path2.length;
}