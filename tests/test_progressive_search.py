import unittest
from unittest.mock import patch
from vega.rocket import RocketBrief, design
from vega.design_search import explore
from vega_geometry.beam import beam
from vega_geometry.topology import mesh_topology


class ProgressiveSearchTests(unittest.TestCase):
    def test_first_result_is_published_before_second_evaluation(self):
        brief=RocketBrief(propellant_model='assumed',propulsion_family='rocket_only',
                          jacket_pattern='none',cooling_passages=0,
                          search_evaluations=8,search_mesh_limit=2)
        events=[]
        def evaluate(b):
            events.append('evaluate')
            return design(b)
        def publish(item):
            events.append('publish')
            self.assertIn('candidates',item['run'])
            return True
        chosen,report=explore(brief,evaluator=evaluate,on_first=publish,compact=True)
        self.assertEqual(events[:3],['evaluate','publish','evaluate'])
        self.assertEqual(report['evaluated'],8)
        self.assertEqual(len(chosen),2)
        self.assertTrue(all(set(row['run'])=={'requirements'} for row in chosen))

    def test_screening_does_not_invoke_expensive_cad(self):
        with patch('vega.assembly.cad_duct',side_effect=AssertionError('CAD invoked')):
            run=design(RocketBrief(propellant_model='assumed'),screening=True)
        self.assertTrue(run['candidates'][0]['assembly']['screening_only'])

    def test_sparse_audit_matches_reference_with_damage(self):
        for mode in ('closed','hole','reversed','nonmanifold'):
            shape=beam([0,0,0],[0,0,10],1,8)
            if mode=='hole':shape['triangles'].pop()
            if mode=='reversed':shape['triangles'][0].reverse()
            if mode=='nonmanifold':shape['triangles'].append(shape['triangles'][0])
            fast=mesh_topology(shape)
            with patch('vega_geometry.topology._sparse_surface_topology',return_value=None):
                reference=mesh_topology(shape)
            self.assertEqual(fast,reference,mode)
