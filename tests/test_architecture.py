import unittest
from copy import deepcopy
from math import pi
from vega.architecture import modules,profile_mesh,display_mesh
import trimesh


class ArchitectureTests(unittest.TestCase):
    def test_closed_annular_input_matches_cylinder_volume(self):
        part=modules()[0];mesh=profile_mesh(part)
        expected=pi*(6**2-4.6**2)*12
        self.assertTrue(mesh.is_volume)
        self.assertLess(abs(mesh.volume-expected)/expected,.001)
        self.assertEqual(len(mesh.split(only_watertight=False)),1)
        invalid=deepcopy(part);invalid['wall']=6
        with self.assertRaises(ValueError):profile_mesh(invalid)

    def test_all_requested_module_inputs_are_closed(self):
        parts=modules()
        self.assertEqual(len({p['id'] for p in parts}),10)
        for part in parts:
            shells=profile_mesh(part).split(only_watertight=False)
            self.assertEqual(len(shells),2 if part['kind']=='regenerator' else 1)
            self.assertTrue(all(s.is_volume for s in shells))

    def test_display_reduction_preserves_a_closed_solid_and_volume(self):
        source=trimesh.creation.icosphere(subdivisions=4,radius=10)
        original_faces=len(source.faces)
        display,reduced=display_mesh(source,3000)
        self.assertTrue(display.is_volume)
        self.assertLess(abs(display.volume-source.volume)/source.volume,.01)
        self.assertEqual(len(source.faces),original_faces)
