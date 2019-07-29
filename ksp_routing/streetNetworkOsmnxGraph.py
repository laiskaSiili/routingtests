import networkx as nx
import osmnx as ox
import numpy as np
from datetime import datetime
import re
import os
from pathlib import Path
from .utilMixin import UtilMixin


class StreetNetworkOsmnxGraph(UtilMixin):

    def __init__(self, user_settings=None):
        super().__init__()
        self._print()
        self.settings.update({
            'city_country': 'Zurich, Switzerland',
            'workspace_path': Path('./Workspace'),
            'try_local_first': True,
            'load_specific_date': None,
            'date_of_download': None,
            'columns_of_interest': ('source', 'target', 'oneway', 'length', 'highway', 'maxspeed', 'lanes', 'geometry'),
        })
        self.settings.update(user_settings if user_settings else {})
        self.settings.update({
            'city_name': self.settings['city_country'].split(',')[0],
        })
        self.data = {
            'multi_graph': None,
            'pseudo_digraph': None,
            'pdg_lookup': None,
            'osmid_to_id0_dict': None,
            'id0_to_osmid_dict': None
        }
        self.initialized = False

        self._run()

    def _run(self):
        self._print()
        self._create_workspace_if_not_exists()
        if self.settings['try_local_first']:
            self._load_from_osmnx_graphml()
        if self.data['multi_graph'] is None:
            self._download_from_osm()
            self._save_as_osmnx_graphml()
        self._create_pseudo_digraph()
        self._create_id_lookup_dicts()
        self._create_digraph_plot()
        self.initialized = True
        self._print(msg='Initialization finished')

    def _download_from_osm(self):
        self._print()
        self.settings['date_of_download'] = datetime.now().strftime('%Y%m%d')
        self.data['multi_graph'] = ox.graph_from_place(self.settings['city_country'], network_type='drive')

    def _save_as_osmnx_graphml(self):
        self._print()
        ox.save_load.save_graphml(
            G=self.data['multi_graph'],
            filename='_'.join([self.settings['city_name'], self.settings['date_of_download'], 'osmnxgraph.graphml']),
            folder=str(self.settings['workspace_path'])
        )

    def _load_from_osmnx_graphml(self):
        self._print()
        # If a specific date for loading is provided, use it to create filename. Otherwise search all files
        # in the workspace and use the newest date (if any exist) to create filename.
        date = ""
        filename = ""
        if self.settings.get('load_specific_date', None):
            date = str(self.settings['load_specific_date'])
            filename = '_'.join([self.settings['city_name'], date, 'osmnxgraph.graphml'])
        else:
            date_re = re.compile('\d{8}')
            potential_dates = [date_re.findall(file) for file in os.listdir(str(self.settings['workspace_path']))
                               if file.startswith(self.settings['city_name'])]
            if potential_dates:
                date = str(max(int(dates[0]) for dates in potential_dates))
                filename = '_'.join([self.settings['city_name'], date, 'osmnxgraph.graphml'])
        # Try to load graph
        try:
            self.data['multi_graph'] = ox.save_load.load_graphml(
                filename=filename,
                folder=str(self.settings['workspace_path'])
            )
            self.settings['date_of_download'] = date
            self._print(msg='Successfully loaded graph from file: ' + filename)
        except (FileNotFoundError, IsADirectoryError):
            pass

    def _create_id_lookup_dicts(self):
        self._print()
        self.data['osmid_to_id0_dict'] = {k: v for k, v in zip(self.data['pseudo_digraph'].nodes, range(len(self.data['pseudo_digraph'])))}
        self.data['id0_to_osmid_dict'] = {v: k for k, v in self.data['osmid_to_id0_dict'].items()}

    def _create_pseudo_digraph(self):
        self._print()
        # get edgelist and multigraph
        el = nx.to_pandas_edgelist(self.data['multi_graph'])[list(self.settings['columns_of_interest'])]
        mg = self.data['multi_graph']
        # prepare pseudo digraph
        pdg = mg.copy()
        # get node pairs that share at least 2 edges
        source_target = [(n1, n2) for n1, n2 in el[['source', 'target']].values]
        unique, counts = np.unique(source_target, return_counts=True, axis=0)
        multi_edges = {tuple(u): c for u, c in zip(unique, counts) if c > 1}
        # get maximum id of current dataset. pseudo-nodes will have ids extending the max to avoid conflicts.
        max_id = np.array(mg.nodes).max()
        pdg_lookup = {}
        for n1, n2 in multi_edges:
            # Initialize lookup table for later use in converting from pseudo digraph to multigraph again.
            # The keys are tuples of (n1, n2), the value is a list, which itself consists of tuples:
            # [(pseudo_n1_id, pseudo_n2_id), (pseudo_n1_id, pseudo_n2_id)]
            # The first tuple references the first multi edge, the second the second multi edge and so on.
            pdg_lookup[(n1, n2)] = []
            nr_edges = len(mg[n1][n2])
            # Loop over all multi edges, starting from key=1. Therefore the first edge with key=0 remains untouched between
            # the original nodes n1, n2.
            for k in range(1, nr_edges):
                # 1. Create pseudo nodes
                # get pseudo node ids and then update max_id
                pseudo_n1_id = max_id + 1
                pseudo_n2_id = max_id + 2
                max_id += 2
                # get node attributes
                n1_attrs = pdg.node[n1].copy()
                n2_attrs = pdg.node[n2].copy()
                # update new node id
                n1_attrs.update({'osmid': pseudo_n1_id})
                n2_attrs.update({'osmid': pseudo_n2_id})
                # add new node ids to lookup table for later use in converting from pseudo digraph to multigraph again
                pdg_lookup[(n1, n2)].append((pseudo_n1_id, pseudo_n2_id))
                # add node to graph
                pdg.add_node(pseudo_n1_id, **n1_attrs)
                pdg.add_node(pseudo_n2_id, **n2_attrs)
                # 2. Connect pseudo nodes to the original nodes using a copy of the edge between n1, n2
                edge = pdg[n1][n2][k].copy()
                # add edge between n1 and n1_pseudo, which has osmid of n1
                pdg.add_edge(n1, pseudo_n1_id, key=0, **edge)
                # add edge between n2_pseudo and n2, which has osmid of n2_pseudo
                edge.update({'osmid': pseudo_n2_id})
                pdg.add_edge(pseudo_n2_id, n2, key=0, **edge)
                # 3. Move multi edges from n1, n2 to new pseudo nodes.
                # edge now has osmid of pseudo_n1
                edge.update({'osmid': pseudo_n1_id})
                # add it to new pseudo nodes and remove between n1 and n2
                pdg.add_edge(pseudo_n1_id, pseudo_n2_id, key=0, **edge)
                pdg.remove_edge(n1, n2, key=k)
        self._print(msg='Finished! A total of {nr_multiedges} multiedges existed.'.format(
            nr_multiedges=len(multi_edges)
        ))
        self.data['pdg_lookup'] = pdg_lookup
        self.data['pseudo_digraph'] = pdg

    def osmid_to_id0(self, ids):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        return [self.data['osmid_to_id0_dict'].get(id, None) for id in ids]

    def id0_to_osmid(self, ids):
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        return [self.data['id0_to_osmid_dict'].get(id, None) for id in ids]

    def _create_digraph_plot(self):
        self._print()
        osmid_to_id0_dict = self.data['osmid_to_id0_dict']
        pdg = self.data['pseudo_digraph'].copy()
        nx.relabel_nodes(pdg, osmid_to_id0_dict, copy=False)
        ox.utils.config(
            imgs_folder=str(self.settings['workspace_path'])
        )
        ox.plot.plot_graph(
            pdg,
            fig_height=40, 
            fig_width=None,
            annotate=True,
            node_color='#66ccff', 
            node_size=15, 
            edge_color='#999999', 
            edge_linewidth=1, 
            edge_alpha=1, 
            use_geom=True,
            show=False,
            close=True,
            save=True,
            file_format='png', 
            filename='_'.join([self.settings['city_name'], self.settings['date_of_download'], 'plot']),
            dpi=300
        )