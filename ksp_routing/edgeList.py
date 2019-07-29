import networkx as nx
import pandas as pd
from .utilMixin import UtilMixin
from geopy import distance as Geopy_Distance
import re
import numpy as np


class EdgeList(UtilMixin):

    def __init__(self, graph_instance, user_settings=None):
        super().__init__()
        assert graph_instance.initialized
        self._graph_instance = graph_instance
        self.settings.update({
            'csv_sep': ',',
            'maxspeed_fallback': 50,
            'lanes_fallback': 2
        })

        self.data = {
            'edgelist_cleaned': None,
            'edgelist_altered': None,
        }
        self.data.update(self._graph_instance.get_data())
        self.settings.update(graph_instance.get_settings())
        self.settings.update(user_settings if user_settings else {})
        self.initialized = False
        self._run()

    def _run(self):
        self._print()
        self._create_workspace_if_not_exists()
        self._write_edge_list(nx.to_pandas_edgelist(self.data['multi_graph']), 'edgelist_raw')
        self._clean_edgelist()
        self._add_simulation_fields()
        self.initialized = True

    def _write_edge_list(self, el, filename):
        full_filename = '_'.join([self.settings['city_name'], self.settings['date_of_download'], filename, '.csv'])
        full_path = str(self.settings['workspace_path'] / full_filename)
        el.to_csv(full_path, sep=self.settings['csv_sep'])

    def _clean_edgelist(self):
        self._print()
        # Generate pseudo digraph edgelist
        pdg = self.data['pseudo_digraph']
        el = nx.to_pandas_edgelist(pdg)
        # Create a copy of the edgelist that will keep track of which records were altered in the cleaning process.
        el_altered = el[['source', 'target']].copy()

        # 1. SOURCE, TARGET
        # Convert source and target and length to numeric, raise exception on error, as the ID columns must be complete.
        # Set source and target as 2d index.
        self._print(msg='Working on: source, target')
        el[['source', 'target']] = el[['source', 'target']].apply(pd.to_numeric, errors='raise')
        self._print(msg='Finished type conversion of source, target.')
        el = el.set_index(['source', 'target'])
        el_altered = el_altered.set_index(['source', 'target'])

        # 2. ONEWAY
        # Convert values to strings, match them against a boolean dictionary to convert them to 1 and 0,
        # then set missing values to -1 and set datatype to int. In a last step, replace -1 with 0, therefore
        # assuming that a road is not a oneway in cases of doubt and set corresponding rows to true in el_altered.
        self._print(msg='Working on: oneway')
        booleanDictionary = {
            True: 1,
            'TRUE': 1,
            'true': 1,
            'True': 1,
            'T': 1,
            False: 0,
            'FALSE': 0,
            'false': 0,
            'False': 0,
            'F': 0
        }
        el['oneway'] = el['oneway'].astype(str).map(booleanDictionary).fillna(-1).astype(int)
        el_altered['oneway'] = False
        el_altered[el['oneway'] == -1] = True
        el[el['oneway'] == -1] = 0

        # 2.1 INSERT MISSING NON ONE WAY
        # Assure that for each two-way street the corresponding links exist. First find set of links that have two-way=0
        # but lack their counterpart. E.g. Index (NodeX, NodeY) exists, but (NodeY, NodeX) is missing.
        # Then extract these links in a copy and reindex with the inversed indices (NodeY, NodeX) instead of original (NodeX, NodeY).
        # Then append these reindexed rows to the original dataframe el.
        el_altered['oneway_insert'] = False
        two_way = el[el['oneway'] == 0]
        missing_counterparts = list(set(two_way.index).difference(set((n2, n1) for n1, n2 in two_way.index)))
        if missing_counterparts:
            reindexed_subset = two_way.loc[missing_counterparts].reindex([(n2, n1) for n1, n2 in missing_counterparts])
            el.append(reindexed_subset)
            # update also edgelist_altered to track later which rows were inserted during this step
            reindexed_altered_subset = el_altered[el['oneway'] == 0].loc[missing_counterparts].reindex([(n2, n1) for n1, n2 in missing_counterparts])
            reindexed_altered_subset['oneway_insert'] = True
            el_altered.append(reindexed_altered_subset)

        self._print(msg='Finished, replaced {nr_boolean} unknown oneway boolean entries. Found and inserted {nr_counterparts} two-way entries missing counterpart.'.format(
            nr_boolean=el_altered['oneway'].sum(),
            nr_counterparts=len(missing_counterparts)
        ))

        # 3. GEOMETRY
        # Convert geometry column to string and select all rows not starting with "LINESTRING" for further processing.
        # Missing geometry is calculated as straight line from start to end node using LineString from shapely.geometry.
        # Corresponding rows in el_altered are set to true.
        self._print(msg='Working on: geometry')
        el['geometry'] = el['geometry'].apply(lambda x: x if str(x).startswith('LINESTRING') else 'nan')
        geom_nan = el['geometry'] == 'nan'
        el_altered['geometry'] = False
        el_altered.loc[geom_nan, 'geometry'] = True
        el.loc[geom_nan, 'geometry'] = ['LINESTRING ({src_x} {src_y}, {trg_x} {trg_y})'.format(
            src_x=pdg.node[src_id]['x'],
            src_y=pdg.node[src_id]['y'],
            trg_x=pdg.node[trg_id]['x'],
            trg_y=pdg.node[trg_id]['y']
        ) for src_id, trg_id in el.loc[geom_nan].index]
        # zip(el.loc[geom_nan, 'source'], el.loc[geom_nan, 'target'])
        self._print(msg='Finished, replaced {} entries.'.format(el_altered['geometry'].sum()))

        # 4. LENGTH
        # Convert length to numeric and set missing values to -1. Then calculate length from geometry.
        # Geopy package is used to calculate the length because the osm coordinates are geographic coordinate system
        # WGS-84 (epsg 4326).
        self._print(msg='Working on: length')
        el['length'] = el['length'].apply(pd.to_numeric, errors='coerce').fillna(-1)
        length_nan = el['length'] == -1
        el_altered['length'] = False
        el_altered[length_nan] = True
        Geopy_Distance.VincentyDistance.ELLIPSOID = 'WGS-84'
        el.loc[length_nan, 'length'] = [
            Geopy_Distance.distance(
                (graph.node[src_id]['x'], graph.node[src_id]['y']),
                (graph.node[trg_id]['x'], graph.node[trg_id]['y'])
            ).meters
            for src_id, trg_id in el.loc[length_nan].index]
        self._print(msg='Finished, replaced {} entries.'.format(el_altered['length'].sum()))

        # 5. HIGHWAY
        # Convert highway to strings. If lists are present, use first value.
        # If no value is present, set to unclassified.
        self._print(msg='Working on: highway')
        el_altered['highway'] = False
        el['highway'] = el['highway'].astype(str)
        highway_temp = ['unclassified' if not x or x == ' ' else x for x in el['highway']]
        highway_temp = [re.findall(r'\w+', x)[0] if x.startswith('[') else x for x in highway_temp]
        el_altered.loc[el['highway'] != highway_temp, 'highway'] = True
        el['highway'] = highway_temp
        self._print(msg='Finished, replaced {} entries.'.format(el_altered['highway'].sum()))

        # 6. MAXSPEED
        # If maxspeed is a list, choose maximum. If maxspeed is missing use lookup table that associates field highway
        # with median of all associated valid max speeds. If no value in lookup table exists, use settings['maxspeed_fallback'].
        self._print(msg='Working on: maxspeed')

        def parse_maxspeed(maxspeed):
            result = -1
            if maxspeed.startswith('['):
                result = max(int(x) for x in re.findall(r'\d+', maxspeed))
            else:
                try:
                    result = int(re.search(r'\d+', maxspeed).group(0))
                except:
                    pass
            return result

        el_altered['maxspeed'] = False
        el['maxspeed'] = el['maxspeed'].astype(str)
        el['maxspeed'] = el['maxspeed'].apply(parse_maxspeed)
        el_altered.loc[el['maxspeed'] == -1, 'maxspeed'] = True
        maxspeed_lookup_df = el.loc[el['maxspeed'] > 0, ['maxspeed', 'highway']].groupby(['highway']).median()
        maxspeed_lookup_dict = {index: row['maxspeed'] for index, row in maxspeed_lookup_df.iterrows()}
        el.loc[el['maxspeed'] == -1, 'maxspeed'] = el.loc[el['maxspeed'] == -1, 'highway'].apply(
            lambda x: maxspeed_lookup_dict.get(x, self.settings['maxspeed_fallback']))
        self._print(msg='Finished, replaced {} entries.'.format(el_altered['maxspeed'].sum()))

        # 7. LANES
        # If lanes is a list, choose maximum of all lanes. If lanes is missing use lookup table that associates field highway
        # with median of all associated valid lanes. If no value in lookup table exists, use value of settings['lanes_fallback'].
        self._print(msg='Working on: lanes')

        def parse_lanes(lanes):
            result = -1
            if lanes.startswith('['):
                result = max(int(x) for x in re.findall(r'\d+', lanes))
            else:
                try:
                    result = int(re.search(r'\d+', lanes).group(0))
                except:
                    pass
            return result

        el_altered['lanes'] = False
        el['lanes'] = el['lanes'].astype(str)
        el['lanes'] = el['lanes'].apply(parse_lanes)
        el_altered.loc[el['lanes'] == -1, 'lanes'] = True
        lanes_lookup_df = el.loc[el['lanes'] > 0, ['lanes', 'highway']].groupby(['highway']).median()
        lanes_lookup_dict = {index: row['lanes'] for index, row in lanes_lookup_df.iterrows()}
        el.loc[el['lanes'] == -1, 'lanes'] = el.loc[el['lanes'] == -1, 'lanes'].apply(
            lambda x: lanes_lookup_dict.get(x, self.settings['lanes_fallback']))
        self._print(msg='Finished, replaced {} entries.'.format(el_altered['lanes'].sum()))

        # 8. SAVE RESULTS IN DATA
        # Add last altered column, that is true if any column in a row was changed.
        el_altered['any_changes'] = el_altered[['oneway', 'geometry', 'length', 'highway', 'maxspeed', 'lanes']].any(
            axis=1)
        self.data['edgelist_altered'] = el_altered
        self.data['edgelist_cleaned'] = el

        # 9. WRITE DATAFRAMES TO CSV
        self._write_edge_list(el, 'edgelist_cleanded')
        self._write_edge_list(el_altered, 'edgelist_altered')

        # Report and finish
        self._print(msg='All finished, rows with at least one change: {changes} / {total} ({percentage:.3f}%)'.format(
            changes=el_altered['any_changes'].sum(),
            total=el.shape[0],
            percentage=el_altered['any_changes'].sum() / el.shape[0] * 100
        ))

    def _add_simulation_fields(self):
        self._print()
        # 1. zero based node ids "source_id0", "target_id0"
        # Replace huge and unordered osm ids with a set of natural numbers starting from 0.
        # Set 2d index using source_id0 and target_id0.
        el = self.data['edgelist_cleaned'].reset_index()
        el['source_id0'] = el['source'].apply(
            lambda x: self.data['osmid_to_id0_dict'][x])
        el['target_id0'] = el['target'].apply(
            lambda x: self.data['osmid_to_id0_dict'][x])
        self.data['edgelist_cleaned'] = el.set_index(['source_id0', 'target_id0'])

        # 2. Free flow time "ta0" and actual link time "ta"
        # Get the free flow time "ta0" of a link in seconds by dividing the link "length" by the "maxspeed".
        # The factor 1000 adjusts for the unit difference of meters ("length") and kilometers ("maxspeed").
        # The factor 3600 adjusts for the unit difference of seconds ("t_a0") and hours ("maxspeed").
        self.data['edgelist_cleaned']['ta0'] = np.array(self.data['edgelist_cleaned']['length'] / self.data['edgelist_cleaned']['maxspeed']
                                                 * 3600 / 1000).astype(int)
        # The actual link time "ta" is set to the freeflow time for now. It will be altered during the simulations.
        self.data['edgelist_cleaned']['ta'] = self.data['edgelist_cleaned']['ta0'].copy()

        # 3. capacity "ca"
        # The capacity "ca" is calculated very simplistic based on the following source:
        # https://www.tmr.qld.gov.au/-/media/busind/techstdpubs/Project-delivery-and-maintenance/Cost-benefit-analysis-manual/42Volumecapacityratio.pdf?la=en
        # Based on the values in table 2, a linear regression is used to estimate hourly capacity based on
        # number of lanes. From table 3, only a single fixed capacity factor of 10 is used to calculate capacity
        # according to equation 4.
        def hourly_capacity_from_lanes(lanes):
            slope = 2200  # from linear regression
            intersect = -1500  # from linear regression
            return int(slope * lanes + intersect)

        self.data['edgelist_cleaned']['ca'] = self.data['edgelist_cleaned']['lanes'].apply(hourly_capacity_from_lanes)

        # 4. volume "va"
        # Add the volume "va", which is the actual number of cars. This is 0, but will be altered during the simulations.
        self.data['edgelist_cleaned']['va'] = 0

        # 5. Report and finish
        self._print(msg='Added freeflow times [s] with min/median/max {ta0_min:.0f}/{ta0_median:.0f}/{ta0_max:.0f}.\n\
        Added capacities [PCE] with min/median/max {ca_min:.0f}/{ca_median:.0f}/{ca_max:.0f}.'.format(
            ta0_min=self.data['edgelist_cleaned']['ta0'].min(),
            ta0_median=self.data['edgelist_cleaned']['ta0'].median(),
            ta0_max=self.data['edgelist_cleaned']['ta0'].max(),
            ca_min=self.data['edgelist_cleaned']['ca'].min(),
            ca_median=self.data['edgelist_cleaned']['ca'].median(),
            ca_max=self.data['edgelist_cleaned']['ca'].max(),
        ))
        self._print(msg='All finished!')
