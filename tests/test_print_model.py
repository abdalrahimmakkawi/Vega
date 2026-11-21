import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vega.demonstrator import recipe
from vega.print_export import clean_native, inspect_mesh, export_print_mesh
import numpy as np
import trimesh


class PrintModelTests(unittest.TestCase):
    def test_print_translation_collapsed_facets_leave_closed_solid(self):
        # A closed tetrahedron with two faces split along a very short edge.
        vertices = [[0,0,0],[1,0,0],[0,1,0],[0,0,1],[1e-7,0,0]]
        faces = [[0,2,4],[4,2,1],[0,4,3],[4,1,3],[0,3,2],[1,2,3]]
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        self.assertTrue(mesh.is_volume)
        mesh.apply_translation([30,0,0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'print.stl'
            self.assertEqual(export_print_mesh(mesh,path),2)
            _, check = inspect_mesh(path)
            self.assertTrue(check['passed'])
            self.assertEqual(check['triangles'],4)
            self.assertAlmostEqual(check['volume_mm3'],1/6)

    def test_job_state_retries_windows_file_locks(self):
        import server
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); target=root/('b'*32+'.json')
            original=Path.replace
            attempts=[]
            def replace(path,destination):
                attempts.append(path)
                if len(attempts)<3:raise PermissionError('Temporary file lock')
                return original(path,destination)
            with patch.object(server,'STATES',root),patch.object(server,'JOBS',{}),patch.object(Path,'replace',replace),patch.object(server.time,'sleep'):
                server.write_json(target,{'status':'complete'})
                self.assertEqual(json.loads(target.read_text())['status'],'complete')
                self.assertEqual(len(attempts),3)

    def test_persistent_file_lock_cannot_hide_a_terminal_job_failure(self):
        import server
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); identity='c'*32
            with patch.object(server,'STATES',root),patch.object(server,'JOBS',{}),patch.object(Path,'replace',side_effect=PermissionError('Locked')),patch.object(server.time,'sleep'):
                with self.assertRaises(PermissionError):
                    server.write_json(root/(identity+'.json'),{'status':'failed','message':'Locked'})
                self.assertEqual(server.job(identity)['status'],'failed')

    def test_only_bounded_resolution_is_accepted(self):
        for value in ([], False, 0, '', {'voxel_mm': True}, {'voxel_mm': float('nan')},
                      {'voxel_mm': .1}, {'voxel_mm': .25}, {'voxel_mm': .5}, {'thrust_n': 1000}, {'wall_mm': .4}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                recipe(value)
        self.assertEqual(recipe({'voxel_mm': .4})['voxel_mm'], .4)

    def test_the_first_model_is_deterministic_and_fixed(self):
        self.assertEqual(recipe(), recipe({'voxel_mm': .2}))
        self.assertEqual(recipe(), recipe())

    def test_lobes_and_open_passages_are_in_the_export_recipe(self):
        result = recipe()
        self.assertEqual(len(result['outer']), 121)
        radii = result['outer'][78]['radii_mm']
        self.assertGreater(max(radii) - min(radii), 4)
        self.assertGreater(min(result['core'][42]['radii_mm']), 3)
        self.assertEqual(result['outer'][0]['z_mm'], 0)
        self.assertEqual(result['outer'][-1]['z_mm'], 120)

    def test_sabre_reference_changes_the_exported_geometry(self):
        low, high = recipe({'reference_flow_g_s':3.5}), recipe({'reference_flow_g_s':4.5})
        self.assertNotEqual(low['outer'], high['outer'])
        self.assertNotEqual(low['synthesis']['geometry']['precooler'], high['synthesis']['geometry']['precooler'])
        self.assertEqual(low['core'][0]['z_mm'], 66)
        self.assertEqual(high['architecture'], 'sabre_inspired_precooled_combined_cycle')

    def test_search_chooses_a_feasible_minimum_and_closes_energy(self):
        from vega.sabre import synthesize
        for flow in (.0035,.004,.0045):
            model=synthesize(flow)
            search=model['search']; selected=search['selected']
            self.assertEqual(len({c['id'] for c in search['candidates']}),search['evaluated'])
            self.assertTrue(selected['feasible'])
            self.assertEqual(selected['score'],min(c['score'] for c in search['candidates'] if c['feasible']))
            thermal=model['equations'][1]['outputs']
            self.assertAlmostEqual(thermal['heat_duty_w'],flow*1005*25)
            self.assertAlmostEqual(thermal['required_surface_mm2']/1e6*1000*thermal['lmtd_k'],thermal['heat_duty_w'])
            self.assertGreaterEqual(selected['surface_area_mm2'],thermal['required_surface_mm2'])
            self.assertGreaterEqual(selected['tube_gap_mm'],1.6)
            if selected['length_mm'] > 18:
                shorter_area = selected['surface_area_mm2']*(1-.2/selected['length_mm'])
                self.assertLess(shorter_area, thermal['required_surface_mm2'])
        with self.assertRaises(ValueError):
            synthesize(.006)

    def test_bundle_screen_rejects_restricted_area_and_checks_outlet(self):
        from vega.sabre import bundle_screen, synthesize
        model = synthesize()
        selected = model['search']['selected']
        screen = selected['bundle_screen']
        ref = model['reference']
        self.assertLess(screen['isothermal_sink_outlet_k'], ref['cooled_temperature_k'])
        self.assertGreater(screen['isothermal_sink_outlet_k'], ref['assumed_coolant_temperature_k'])
        self.assertAlmostEqual(screen['open_area_mm2'] * screen['midspan_velocity_m_s'],
                               screen['required_area_mm2'] * ref['intake_speed_m_s'])
        restricted = bundle_screen(ref, selected, 20.)
        self.assertGreater(restricted['midspan_velocity_m_s'], ref['intake_speed_m_s'])
        self.assertFalse(restricted['flow_area_passed'])

    def test_cleanup_rejects_a_detached_print_part(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mesh.stl'
            big = trimesh.creation.box([10, 10, 10])
            small = trimesh.creation.box([.1, .1, .1])
            small.apply_translation([8, 0, 0])
            trimesh.util.concatenate([big, small]).export(path)
            with self.assertRaisesRegex(ValueError, 'Detached material'):
                clean_native(path, .4)

    def test_cleanup_reports_only_small_enclosed_cavities(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mesh.stl'
            outer = trimesh.creation.box([10, 10, 10])
            inner = trimesh.creation.box([.2, .2, .2])
            inner.invert()
            trimesh.util.concatenate([outer, inner]).export(path)
            audit = clean_native(path, .4)
            self.assertEqual(audit['removed_shells'], 1)
            self.assertAlmostEqual(audit['filled_cavity_mm3'], .008, places=6)
            mesh, check = inspect_mesh(path)
            self.assertTrue(check['passed'])
            self.assertAlmostEqual(mesh.volume, 1000)

    def test_large_cavity_and_open_shell_are_not_silently_repaired(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mesh.stl'
            outer = trimesh.creation.box([10, 10, 10])
            inner = trimesh.creation.box([3, 3, 3]); inner.invert()
            trimesh.util.concatenate([outer, inner]).export(path)
            with self.assertRaises(ValueError):
                clean_native(path, .4)
            outer.update_faces(np.arange(len(outer.faces)-1)); outer.export(path)
            with self.assertRaises(ValueError):
                clean_native(path, .4)

    def test_changed_or_failed_artifact_cannot_be_downloaded(self):
        import server
        from vega.print_export import digest
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity = 'a'*32
            folder = root / identity; folder.mkdir()
            artifact = folder / 'half-a.stl'; artifact.write_bytes(b'checked')
            (folder / 'manifest.json').write_text(json.dumps({'half-a.stl': digest(artifact)}))
            (root / (identity + '.json')).write_text(json.dumps({'status': 'complete'}))
            with patch.object(server, 'DATA', root), patch.object(server, 'STATES', root):
                self.assertEqual(server.verified_file(identity, 'half-a.stl'), artifact)
                artifact.write_bytes(b'changed')
                self.assertIsNone(server.verified_file(identity, 'half-a.stl'))
                artifact.write_bytes(b'checked')
                (root / (identity + '.json')).write_text(json.dumps({'status': 'failed'}))
                self.assertIsNone(server.verified_file(identity, 'half-a.stl'))


if __name__ == '__main__':
    unittest.main()
