import unittest
from dataclasses import replace
from vega.rocket import RocketBrief, design
from vega.assembly import build_assembly
from vega_geometry.topology import reachable


class AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief=RocketBrief(propellant_model='assumed',inlet_capture_area_m2=.08,inlet_length_m=.6)
        cls.candidate=design(cls.brief)['candidates'][0]
        cls.assembly=cls.candidate['assembly']

    def test_shared_interfaces_and_native_scale(self):
        a=self.assembly
        self.assertTrue(all(a['checks'].values()))
        self.assertEqual(a['core_placement']['scale'],1)
        self.assertEqual({c['id'] for c in a['components']},
            {'air_inlet','mixer','isolator','air_combustor','common_nozzle','frame',
             'thermal_reinforcement','mixer_strakes','core_mounts'})
        for before,after in zip(a['sections'],a['sections'][1:]):self.assertEqual(before[-1],after[0])
        self.assertEqual(a['core_placement']['exit_z_mm'],a['sections'][1][0]['z_mm'])
        self.assertGreaterEqual(a['core_placement']['minimum_z_mm'],0)
        for source in ('air_inlet','fuel_tank','oxidizer_tank'):
            self.assertTrue(reachable(a['topology']['flow']['edges'],source,'common_nozzle'))

    def test_length_change_moves_all_downstream_components(self):
        b=build_assembly(replace(self.brief,mixer_length_dh=3),self.candidate)
        self.assertNotEqual(b['recipe_sha256'],self.assembly['recipe_sha256'])
        shift=b['sections'][1][-1]['z_mm']-self.assembly['sections'][1][-1]['z_mm']
        self.assertGreater(shift,0)
        for index in range(2,5):
            self.assertAlmostEqual(b['sections'][index][-1]['z_mm']-self.assembly['sections'][index][-1]['z_mm'],shift)

    def test_topology_option_changes_actual_mesh_and_graph(self):
        b=build_assembly(replace(self.brief,frame_topology='rails'),self.candidate)
        self.assertLess(b['topology']['frame']['cycle_rank'],self.assembly['topology']['frame']['cycle_rank'])
        self.assertNotEqual(b['scene_sha256'],self.assembly['scene_sha256'])
        self.assertEqual(b['topology']['frame']['connected_components'],1)
        self.assertTrue(all(b['checks'].values()))

    def test_optimized_frame_uses_volume_and_changes_exported_geometry(self):
        optimized=self.assembly['frame_optimization']
        self.assertIsNotNone(optimized)
        self.assertLess(optimized['optimized_compliance_n_mm'],optimized['baseline_uniform_compliance_n_mm'])
        self.assertLessEqual(optimized['volume_fraction_actual'],self.brief.frame_volume_fraction+1e-4)
        self.assertLess(optimized['selected_member_count'],optimized['candidate_member_count'])
        self.assertGreater(max(optimized['edge_radii_mm'].values())-min(optimized['edge_radii_mm'].values()),1)
        lean=build_assembly(replace(self.brief,frame_volume_fraction=.5),self.candidate)
        self.assertLess(lean['frame_optimization']['volume_fraction_actual'],optimized['volume_fraction_actual'])
        self.assertNotEqual(lean['scene_sha256'],self.assembly['scene_sha256'])
        self.assertTrue(all(lean['checks'].values()))

    def test_unsupported_family_does_not_invent_turbine(self):
        self.assertEqual(build_assembly(replace(self.brief,propulsion_family='tbcc'),self.candidate)['status'],'unsupported_family')
        self.assertEqual(build_assembly(replace(self.brief,propulsion_family='rocket_only'),self.candidate)['status'],'not_requested')

    def test_exported_frame_matches_analyzed_straight_bars(self):
        import math
        a=self.assembly;nodes=a['topology']['frame']['nodes']
        optimized=a['frame_optimization'];members=a['frame_members']
        self.assertEqual(len(members),optimized['selected_member_count'])
        for member in members:
            start,end=member['nodes']
            self.assertEqual(member['start_mm'],nodes[start])
            self.assertEqual(member['end_mm'],nodes[end])
            self.assertAlmostEqual(member['length_mm'],math.dist(nodes[start],nodes[end]))
            self.assertEqual(member['radius_mm'],optimized['edge_radii_mm'][start+'|'+end])
        body=next(b for b in a['scene']['bodies'] if b['component_id']=='frame')
        # One 32-sided closed cylinder per analyzed bar and radial attachment.
        self.assertEqual(body['triangle_count'],128*(len(members)+len(nodes)//2))

    def test_disabled_cooling_has_direct_fuel_route(self):
        a=design(replace(self.brief,cooling_passages=0))['candidates'][0]['assembly']
        self.assertNotIn('cooling',a['topology']['flow']['nodes'])
        self.assertIn(['fuel_tank','fuel_feed'],a['topology']['flow']['edges'])
        self.assertIn(['fuel_feed','injector'],a['topology']['flow']['edges'])
        self.assertNotIn('fuel_return',a['topology']['flow']['nodes'])
