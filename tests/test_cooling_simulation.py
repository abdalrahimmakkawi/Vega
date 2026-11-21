import unittest
from math import pi
from copy import deepcopy
from vega.cooling_simulation import solve_network,collector_edges,assembly_network
from vega.demonstrator import recipe
from vega.architecture import modules
from vega.bell_cooling import geometry

class NetworkTests(unittest.TestCase):
    def test_single_pipe_matches_poiseuille(self):
        e=dict(id='pipe',**{'from':'in','to':'out'},length_mm=100,radius_mm=1,group='test')
        r=solve_network([e],'in','out',10)
        expected=8*1.8e-5*.1/(pi*.001**4)*10e-6
        self.assertAlmostEqual(r['required_pressure_difference_pa'],expected)
        self.assertLess(r['relative_mass_balance_residual'],1e-12)
    def test_parallel_pipe_split_obeys_radius_to_fourth_power(self):
        edges=[dict(id=str(r),**{'from':'in','to':'out'},length_mm=100,radius_mm=r,group='test') for r in [1,2]]
        result=solve_network(edges,'in','out',10)
        self.assertAlmostEqual(result['edges'][1]['flow_ml_s']/result['edges'][0]['flow_ml_s'],16)
    def test_invalid_dimensions_and_flow_rejected(self):
        for q in [True,0,-1,float('nan'),31]:
            with self.assertRaises(ValueError):solve_network([],'in','out',q)

    def test_disconnected_graph_is_rejected(self):
        edges=[dict(id=str(i),**{'from':a,'to':b},length_mm=10,radius_mm=1) for i,(a,b) in enumerate([('in','out'),('a','b')])]
        with self.assertRaisesRegex(ValueError,'Disconnected'):solve_network(edges,'in','out')

    def test_collector_splits_saved_polyline_and_conserves_length(self):
        collector=dict(points=[[0,0,0],[10,0,0],[10,10,0],[0,10,0],[0,0,0]],bore_radius_mm=1.3)
        edges,mapping=collector_edges('ring',collector,dict(a=[5,0,0],b=[0,5,0]))
        self.assertEqual(sorted(e['length_mm'] for e in edges),[10,30])
        self.assertTrue(all(e['radius_mm']==1.3 for e in edges))
        # Two parallel arcs: 10 and 30 mm pipes -> 7.5 mm equivalent.
        network=solve_network(edges,mapping['a'],mapping['b'],10)
        expected=8*1.8e-5*.0075/(pi*.0013**4)*10e-6
        self.assertAlmostEqual(network['required_pressure_difference_pa'],expected)
        self.assertLess(network['relative_energy_balance_residual'],1e-12)
        with self.assertRaisesRegex(ValueError,'Disconnected collector'):
            collector_edges('ring',collector,dict(a=[5,0,0],b=[0,5,1]))

    def test_assembly_uses_actual_bores_and_detects_detached_geometry(self):
        design=recipe();design['architecture_modules']=modules();cooling=geometry(design)
        original=assembly_network(design,cooling)
        self.assertEqual(len(original['edges']),40)
        altered=deepcopy(cooling);altered['branches'][0]['bore_radius_mm']*=.5
        changed=assembly_network(design,altered)
        resistance=lambda network:next(e['resistance_pa_s_m3'] for e in network['edges'] if e['id']=='bell-1')
        self.assertAlmostEqual(resistance(changed)/resistance(original),16)
        self.assertGreater(changed['required_pressure_difference_pa'],original['required_pressure_difference_pa'])
        altered=deepcopy(cooling);altered['branches'][0]['points'][0][2]+=1
        with self.assertRaisesRegex(ValueError,'Disconnected'):assembly_network(design,altered)
        altered=deepcopy(cooling);altered['supply'][0][0]+=1
        with self.assertRaisesRegex(ValueError,'Disconnected'):assembly_network(design,altered)
