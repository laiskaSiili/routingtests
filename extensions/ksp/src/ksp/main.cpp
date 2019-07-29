#include "ksp.hpp"
#include <iostream>
#include <boost/algorithm/string.hpp>

using namespace std;

int main() {

	string path = "C:\\Users\\mfolini\\Desktop\\ksp2\\src\\ksp\\sample\\sample.gr";
	double start = 0;
	double target = 4;
	double theta = 0.6;
	string algo = "mp";
	double k = 3;

	vector< vector<double> > res = k_shortest_paths(path, k, theta, start, target, algo);
	for (double i = 0; i < res.size(); i++) {
		cout << "Length: ";
		cout << res[i][0] << " | ";
		for (double j = 1; j < res[i].size(); j++) {
			cout << res[i][j] << " ";
		}
		cout << endl;
	}

	return 0;
}