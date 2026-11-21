import json
import tempfile
import unittest
from pathlib import Path
import trimesh
from vega.integration import inside_stl,interior_probes,specification,rounded_route


class IntegrationTests(unittest.TestCase):
    def test_contact_audit_distinguishes_air_from_material(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'cube.stl'
            trimesh.creation.box(extents=[4,4,4]).export(path)
            self.assertTrue(all(inside_stl(path,interior_probes([1,0,0]))))
            self.assertEqual(inside_stl(path,[[3,0,0],[0,0,0],[-3,0,0]]),[False,True,False])
            with self.assertRaises(ValueError):inside_stl(path,[[0,0,0]],count=999)

    def test_contact_audit_respects_packed_component_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'two.stl'
            a=trimesh.creation.box(extents=[2,2,2]);b=a.copy();b.apply_translation([5,0,0])
            trimesh.util.concatenate([a,b]).export(path)
            self.assertEqual(inside_stl(path,[[0,0,0],[5,0,0]],len(a.faces),len(b.faces)),[False,True])

    def test_closed_inputs_and_all_static_parts_have_connections(self):
        parts,joints=specification()
        for part in parts:
            self.assertTrue(all(m.is_volume for m in part.pop('seeds')))
        json.dumps(parts,allow_nan=False)
        sources={j['source'] for j in joints}
        self.assertEqual(len(sources-{'aft-coupling'}),15)
        self.assertNotIn('centrebody',sources)
        self.assertTrue(all(len(j['probes'])==7 for j in joints))

    def test_rounded_route_preserves_terminals(self):
        route=rounded_route([[0,0,0],[10,0,0],[10,10,0]])
        self.assertEqual(route[0],[0,0,0]);self.assertEqual(route[-1],[10,10,0])
        self.assertNotIn([10,0,0],route)
