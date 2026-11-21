import unittest
from copy import deepcopy
from math import pi
from vega.demonstrator import recipe
from vega.cem import channel_network, acceptance
from vega.input_mesh import shell_mesh


class SpecializedCEMTests(unittest.TestCase):
    def test_redesign_changes_export_profiles_and_keeps_air_corridor_open(self):
        r=recipe()
        self.assertEqual(r['voxel_mm'],.2)
        self.assertAlmostEqual(r['core'][-1]['radii_mm'][0],8.5)
        self.assertAlmostEqual(r['outer'][-1]['radii_mm'][0],17.2)
        self.assertGreater(min(min(row['radii_mm']) for row in r['outer']),15.4)
        self.assertEqual(r['design_changes']['exit_collar_outer_diameter_mm'],42.)

    def test_parallel_network_matches_analytic_solution_and_scaling(self):
        routes=[dict(id=str(i),points=[[0,0,0],[0,0,100]],bore_radius_mm=1.) for i in range(4)]
        a=channel_network(routes,20)
        expected=8*1.8e-5*.1/(pi*.001**4)*(20e-6/4)
        self.assertAlmostEqual(a['branch_only_pressure_drop_pa'],expected)
        self.assertLess(abs(a['mass_residual_kg_s']),1e-12)
        doubled=channel_network(routes,40)
        self.assertAlmostEqual(doubled['branch_only_pressure_drop_pa'],2*expected)
        routes[0]['points'][-1][-1]=200
        uneven=channel_network(routes,20)['branches']
        self.assertAlmostEqual(uneven[0]['flow_ml_s']*2,uneven[1]['flow_ml_s'])

    def test_rejects_invalid_network_inputs(self):
        routes=recipe()['cooling']['routes']
        for value in (True,0,-1,61,float('nan'),'40'):
            with self.assertRaises(ValueError):channel_network(routes,value)

    def test_coarse_voxels_resize_channels_without_relaxing_wall_requirement(self):
        fine=recipe({'voxel_mm':.4});coarse=recipe({'voxel_mm':.7})
        self.assertAlmostEqual(fine['cooling']['network']['nominal_bore_diameter_mm'],1.6)
        self.assertAlmostEqual(coarse['cooling']['network']['nominal_bore_diameter_mm'],2.1)
        for route in coarse['cooling']['routes']:
            self.assertAlmostEqual(route['outer_radius_mm']-route['bore_radius_mm'],1.2)
        self.assertEqual(coarse['cem']['requirements']['voxel_mm'],.7)
        self.assertLess(coarse['cem']['channel_network']['branch_only_pressure_drop_pa'],fine['cem']['channel_network']['branch_only_pressure_drop_pa'])

    def test_specialization_has_no_active_propulsion_and_tracks_provenance(self):
        r=recipe();cem=r['cem']
        self.assertNotIn('cycle',r)
        self.assertNotIn('transitions',r)
        self.assertEqual(cem['specialization'],'non_firing_airflow_cooling_demonstrator')
        self.assertFalse(cem['physical_validation_passed'])
        self.assertEqual(cem['analysis_sha256'],recipe()['cem']['analysis_sha256'])
        changed=recipe({'cooling_flow_ml_s':20})
        self.assertNotEqual(r['recipe_sha256'],changed['recipe_sha256'])
        self.assertAlmostEqual(cem['channel_network']['branch_only_pressure_drop_pa'],2*changed['cem']['channel_network']['branch_only_pressure_drop_pa'])
        visited=set()
        for stage in cem['stages']:
            self.assertTrue(set(stage['depends_on'])<=visited)
            visited.add(stage['id'])

    def test_triangle_shell_has_expected_volume_and_outward_winding(self):
        rows=[dict(z_mm=z,radii_mm=[10.]*120) for z in (0,5,10)]
        mesh=shell_mesh(rows,2)
        self.assertTrue(mesh.is_volume)
        self.assertEqual(len(mesh.split()),1)
        self.assertAlmostEqual(mesh.volume,pi*(12**2-10**2)*10,delta=1.)
        self.assertEqual(len(mesh.faces),4*120*3)

    def test_native_conversion_gate_cannot_be_skipped(self):
        cem=recipe()['cem'];part={'passed':True}
        native=dict(geometry_pipeline='triangle_mesh_to_voxels_then_implicit_booleans',input_triangle_count=100,cooling_clearance_samples=1,
            boolean_reference_samples=15,boolean_operations={'Add':1,'Subtract':1,'Intersect':1})
        mesh=dict(triangles=100,passed=True)
        result=acceptance(cem,native,part,{'a':part,'b':part},mesh)
        self.assertFalse(result['physical_validation_passed'])
        self.assertTrue(any(c['status']=='pending' for c in cem['checks']))
        for key in ('geometry_pipeline','input_triangle_count','cooling_clearance_samples','boolean_reference_samples','boolean_operations'):
            invalid=deepcopy(native);invalid.pop(key)
            with self.assertRaises(ValueError):acceptance(cem,invalid,part,{'a':part,'b':part},mesh)


if __name__=='__main__':unittest.main()
