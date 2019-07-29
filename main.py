from pathlib import Path
from ksp_routing.streetNetworkOsmnxGraph import StreetNetworkOsmnxGraph
from ksp_routing.edgeList import EdgeList

if __name__ == '__main__':
    from pathlib import Path
    from ksp_routing.streetNetworkOsmnxGraph import StreetNetworkOsmnxGraph
    from ksp_routing.edgeList import EdgeList
    from ksp_routing.simulation import Simulation

    print('go')

    settings = {
        'city_country': 'Zurich, Switzerland',
        'workspace_path': Path('./Workspace'),
        'try_local_first': True,
        'load_specific_date': None,
    }

    simulation_settings = {
        'result_settings': {
            'aggregate_functions': [],
            'record_drop_info': True,
        },
        'scenario_params': {
            'shape': (1, 4, 8, 12),
            'K': (2, 3, 4, 5),
            'source_target': ((3910, 2905), (1629, 2195), (4439, 414), (1053, 576), (456, 4022)),
            'total_travel': (4000, 8000, 16000, 32000, 64000, 96000),
            'drop_interval': (100, 1000, 10000, 100000),
            'mode': (0, 1),
            'theta': (0.25, 0.33, 0.5),
            'algorithm': ('opplus',)
        },
        'force_fw_calculation': False,
        'force_scenarios_calculation': False,
    }

    simulation_settings['scenario_params'].update({
        'shape': (4,),
        'K': (4, 5),
        'source_target': ((3712, 3785),),
        'total_travel': (32000, 64000),
        'drop_interval': (15000,),
        'mode': (0,),
        'theta': (0.5,),
    })

    graph = StreetNetworkOsmnxGraph(settings)
    edgelist = EdgeList(graph)
    simulation = Simulation(edgelist, simulation_settings)

    print('finished')

