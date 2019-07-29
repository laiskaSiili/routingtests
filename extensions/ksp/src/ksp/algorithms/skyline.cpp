/*
Copyright (c) 2017 Theodoros Chondrogiannis
*/

#include "kspwlo.hpp"

void SkylineContainer::insert(OlLabel* msv) {
	if(!this->contains(msv->node_id)) {
		vector<OlLabel*> newVector;
		newVector.push_back(msv);
		container.insert(make_pair(msv->node_id,newVector));
	}
	else {
		container[msv->node_id].push_back(msv);
	}
}

bool SkylineContainer::contains(double id) {
	if(container.find(id) != container.end())
		return true;
	return false;
}

vector<OlLabel*> SkylineContainer::get(double id) {
	return container[id];
}

long SkylineContainer::contentsSize() {
	long contentsSize = 0;
	
	for(unordered_map<double,vector<OlLabel*>>::iterator iterator = container.begin(); iterator != container.end(); iterator++) {
		contentsSize += iterator->second.size();
	}

	return contentsSize;
}

bool SkylineContainer::dominates(OlLabel* current) {
	
	if(!this->contains(current->node_id))
		return false;

	for(double i=0;i<container[current->node_id].size();i++) {
		OlLabel* temp = container[current->node_id].at(i);
		bool flag = true;
		
		for(double j=0;j<current->overlapList.size();j++) {
			if(current->overlapList[j] < temp->overlapList[j]) {
				flag = false;
				break;
			}
		}
		if(flag)
			return true;
	}
	return false;
}