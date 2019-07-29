from .utilMixin import UtilMixin
import itertools
from pathos.pools import ProcessPool
from numpy.random import beta
import numpy as np
from random import randint
from os.path import isfile
from os import remove

#########################################
# k-shortest Paths with limited overlap
# FROM: https://github.com/tchond/kspwlo
#########################################
from ksp import k_shortest_paths

#########################################
# Assignment package used for FW
# FROM: https://github.com/nlperic/ta-lab
#########################################
#from TrivikGPS.assignment.assign import msa, frank_wolfe
#from TrivikGPS.assignment.graph import *


class Simulation(UtilMixin):

    def __init__(self, edgelist_instance, user_settings=None):
        super().__init__()
        assert edgelist_instance.initialized
        self._edgelist_instance = edgelist_instance
        self.settings.update({
            'scenario_id_order': ('source_target', 'total_travel', 'drop_interval', 'mode', 'shape', 'K', 'theta', 'algorithm'),
            'alpha': 0.15,
            'beta': 4,
            'capacity_cutoff': 3,
            'cols_in_result': ['source', 'target', 'ta0', 'ta', 'ca', 'va', 'length'], #source_id0 and target_id0 are also in results as they are the 2d row index.
            'n_cpus': 3,
        })
        self.settings.update(edgelist_instance.get_settings())
        self.settings.update(user_settings if user_settings else {})
        self.data = {}
        self.data.update(self._edgelist_instance.get_data())
        self.data.update({
            'nr_nodes': len(self.data['osmid_to_id0_dict']),
            'nr_edges': self.data['edgelist_cleaned'].shape[0]
        })
        self.scenarios = None
        self.initialized = False
        self._run()

    def _run(self):
        self._generate_scenarios()
        # self._process_fw()
        self._process_scenarios()

    def _generate_scenarios(self):
        self._print()
        scenario_params = self.settings['scenario_params']
        scenario_id_order = self.settings['scenario_id_order']
        self.scenarios = tuple(itertools.product(*[scenario_params[key] for key in scenario_id_order]))

    def _process_scenarios(self):
        self._print()
        scenarios_results_list = ProcessPool(ncpus=self.settings['n_cpus']).map(self._calculate_scenario, self.scenarios)
        scenarios_results_dict = {
            'scenario_id_name_ordering': self.settings['scenario_id_order'],
            'scenarios_summary': self.settings['scenario_params'],
            'scenarios': {scenario_id: scenario_data for scenario_id, scenario_data in scenarios_results_list}
        }
        for k, v in scenarios_results_dict['scenarios'].items():
            print(str(k) + ': ' + v['status'] + ' | ' + v['status_detail'])
        self._print(msg='Finished KSP scenarios')

    def _calculate_scenario(self, scenario_params):
        def beta_path_selection_factory(nr_paths, mode, shape):
            minimum = 0
            maximum = nr_paths
            assert (minimum != maximum)
            mean = (minimum + shape * mode + maximum) / (shape + 2)
            a = (shape + 2) * (mean - minimum) / (maximum - minimum)
            b = (shape + 2) * (maximum - mean) / (maximum - minimum)
            assert (a > 0 and b > 0 and shape >= 0)

            def get_route_index(n=1):
                return (beta(a, b, n) * (maximum - minimum) // 1) + minimum

            return get_route_index

        def apply_bpr_to_row(row):
            # if row['va'] / row['ca'] > self.settings['capacity_cutoff']:
            #     print(str(row['va'] / row['ca']) + ' <> ' + str(self.settings['capacity_cutoff']) + ' -> ' + str(min(row['va'] / row['ca'], self.settings['capacity_cutoff'])))
            capacity_utilization = min(row['va'] / row['ca'], self.settings['capacity_cutoff'])
            #capacity_utilization = row['va'] / row['ca']
            ta = row['ta0'] * (1 + self.settings['alpha'] * np.power(capacity_utilization, self.settings['beta']))
            return int(ta)

        def write_ksp_edgelist_factory(el, workspace_path):
            # Target format is a first line containing meta data abour nr nodes and edges, then 3 entries per line
            # describing an edge by from_node id, to_node id and associated weight.
            meta_header = np.array([self.data['nr_nodes'], self.data['nr_edges'], 0], dtype=np.int64)
            ids_array = el.reset_index()[['source_id0', 'target_id0']].values
            # Add a column of zeros to be replaced by weight column later on
            ids_array_with_weight_placeholder = np.hstack((ids_array, np.zeros((ids_array.shape[0], 1), dtype=ids_array.dtype)))
            matrix_with_meta_header = np.vstack((meta_header, ids_array_with_weight_placeholder))

            def write_ksp_edgelist(weight_array):
                matrix_with_meta_header[1:, 2] = weight_array
                matrix_with_meta_header.astype(np.int64)
                while True:
                    possible_path = str(workspace_path / 'temp_ksp_edgelist_p') + str(randint(1, 1000000)) + '.gr'
                    if not isfile(possible_path):
                        break
                np.savetxt(possible_path, matrix_with_meta_header, delimiter=" ", fmt='%s')
                return possible_path

            return write_ksp_edgelist

        def valid_path_weight(el, path):
            weight_from_k_shortest_path_function = path[0]
            source_target = ((source, target) for source, target in zip(path[1:-1], path[2:]))
            control_weight = el.loc[source_target, 'ta'].sum()
            # print(str(scenario_params) + ' | ' + str(weight_from_k_shortest_path_function) + ' <--> ' + str(control_weight) + ' => ' + str(abs(weight_from_k_shortest_path_function - control_weight) < 0.01 * control_weight))
            return abs(weight_from_k_shortest_path_function - control_weight) < (0.01 * control_weight)

        workspace_path = self.settings['workspace_path']
        scenario_id_order = self.settings['scenario_id_order']
        k = int(scenario_params[scenario_id_order.index('K')])
        source, target = scenario_params[scenario_id_order.index('source_target')]
        shape = scenario_params[scenario_id_order.index('shape')]
        mode = scenario_params[scenario_id_order.index('mode')]
        theta = float(scenario_params[scenario_id_order.index('theta')])
        total_travel = scenario_params[scenario_id_order.index('total_travel')]
        drop_interval = scenario_params[scenario_id_order.index('drop_interval')]
        algorithm = scenario_params[scenario_id_order.index('algorithm')]

        #print('START scenario_params: Total Travels: {} | Drop Interval: {} | Source/Target: {}/{} | Mode: {} | Shape: {} | K: {} | Theta: {}'
        #      .format(total_travel, drop_interval, source, target, mode, shape, k, theta))

        el = self.data['edgelist_cleaned'][self.settings['cols_in_result']].copy()
        write_ksp_edgelist = write_ksp_edgelist_factory(el, workspace_path)
        get_route_index = beta_path_selection_factory(k, mode, shape)

        result_dict_scenario = {
            'status': 'OK',
            'status_detail': '',
            'drop': {},
            'last_drop_index': None,
            'edge_list': None,
            'used_edge_ids': None,
        }

        used_edge_ids = set()
        travels_left = total_travel
        drop_counter = 0
        while travels_left > 0:
            travels_dropped = total_travel - travels_left
            temp_file_ksp_edgelist = write_ksp_edgelist(el['ta'].values)
            # calculate k-shortest paths. The resulting object is a nested list.
            # Each nested list stands for a path, whereby the first entry indicates the
            # cumulated weight along the path. The following entries are the node ids of the path.
            paths = k_shortest_paths(temp_file_ksp_edgelist, k, theta, source, target, algorithm)
            # check if overflow error occured by checking if path[k][0] == 0.
            for path in paths:
                if not valid_path_weight(el, path):
                    result_dict_scenario['status'] = 'OVERFLOW'
                    result_dict_scenario[
                        'status_detail'] = 'An overflow error occured for the weights in drop {d}'.format(
                        d=drop_counter
                    )
                    return scenario_params, result_dict_scenario
            # if everything was fine, remove path weights from path lists.
            paths = [path[1:] for path in paths]
            # check if k paths were found. If not, set status accordingly and return.
            print(' --- Drop: ' + str(drop_counter) + ' | ' + str(scenario_params) + ' | LEN PATHS: ' + str(len(paths)) + ' | K=' + str(k))
            if len(paths) < k:
                result_dict_scenario['status'] = 'LACKING PATHS'
                result_dict_scenario['status_detail'] = 'Found only {np} paths instead of k ({k}) in drop {d}'.format(
                    np=len(paths),
                    k=k,
                    d=drop_counter
                )
                return scenario_params, result_dict_scenario
            n_travels = drop_interval if travels_left > drop_interval else travels_left
            path_choices = get_route_index(n_travels)
            path_indices, nr_cars = np.unique(path_choices, return_counts=True)
            for path_index, nr_car in zip(path_indices, nr_cars):
                path = paths[int(path_index)]
                source_target = [(source, target) for source, target in zip(path[:-1], path[1:])]
                el.loc[source_target, 'va'] = el.loc[source_target, 'va'] + nr_car
                el['ta'] = el.apply(apply_bpr_to_row, axis=1)
                used_edge_ids = used_edge_ids.union(set(source_target))
            travels_left -= n_travels
            remove(temp_file_ksp_edgelist)

            result_dict_scenario['drop'][drop_counter] = {
                'total_travels_this_drop': travels_dropped + n_travels,
                'drop_size': n_travels,
                'path_choices': [(int(i), int(n)) for i, n in zip(path_indices, nr_cars)],
                'paths': paths,
                'edge_list': el.loc[list(used_edge_ids)].copy(),
                'used_edge_ids': list(used_edge_ids),
            }
            drop_counter += 1
        result_dict_scenario['last_drop_index'] = (total_travel - 1) // drop_interval
        result_dict_scenario['edge_list'] = el.loc[list(used_edge_ids)].copy()
        result_dict_scenario['used_edge_ids'] = list(used_edge_ids)
        print(
            'FINISHED scenario_params: Total Travels: {} | Drop Interval: {} | Source/Target: {}/{} | Mode: {} | Shape: {} | K: {} | Theta: {}'.format(
                total_travel, drop_interval, source, target, mode, shape, k, theta))
        return scenario_params, result_dict_scenario

    def _process_fw(self):
        self._print()
        totaltravels = self.settings['scenario_params']['total_travel']
        source_target = self.settings['scenario_params']['source_target']
        fw_params = tuple([(od, tt) for od in source_target for tt in totaltravels])
        fw_results_list = ProcessPool().map(self._calculate_fw, fw_params)
        fw_results_dict = {
            'scenario_id_name_ordering': ('source_target', 'total_travel'),
            'scenarios_summary': {
                'source_target': source_target,
                'total_travel': totaltravels,
            },
            'scenarios': {fw_id: fw_data for fw_id, fw_data in fw_results_list}
        }
        print(fw_results_dict)
        self._print(msg='Finished FW scenarios')

    def _calculate_fw(self, fw_param):
        print('Call _calculate_fw(): ' + str(fw_param))
        source_target, total_travel = fw_param
        source, target = source_target
        origins = [source]
        destinations = [target]
        od_flow = {
            source: {target: total_travel}
        }
        network = Network('net')
        alpha = self.settings['alpha']
        beta = str(self.settings['beta'])
        el = self.data['edgelist_cleaned'][self.settings['cols_in_result']].copy()
        for od_pair, row in el.iterrows():
            edge_id = od_pair
            pointer, pointee = od_pair
            freeflowtime = row['ta0']
            capacity = row['ca']
            edge_info = (edge_id, pointer, pointee, freeflowtime, capacity, alpha, beta)
            network.add_edge(Edge(edge_info))
        link_volumes = frank_wolfe(network, od_flow, origins, destinations)
        network.update_cost(link_volumes)

        for k, v in link_volumes.items():
            print(str(k) + ' ->> ' + str(v))

        used_edge_ids, volumes = zip(*[(k, v) for k, v in link_volumes.items() if v > 0.01])
        used_edge_ids = list(used_edge_ids)
        volumes = list(volumes)
        el['ta'] = 0
        el['va'] = 0
        el.loc[used_edge_ids, ['va']] = volumes
        el.loc[used_edge_ids, ['ta']] = [network.edgeset[edge_id].cost for edge_id in used_edge_ids]

        results_fw_dict = {
            'used_edge_ids': used_edge_ids,
            'edge_list': el.loc[used_edge_ids].copy(),
        }
        print('Return _calculate_fw(): ' + str(fw_param))
        return (source_target, total_travel), results_fw_dict

