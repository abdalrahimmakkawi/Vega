import math
import struct
import unittest
from vega.stl import validate_binary_stl, surface_acceptable


def sample():
    return bytes(80) + struct.pack('<I12fH', 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0)


class STLTests(unittest.TestCase):
    def test_surface_acceptance_requires_consistent_positive_solid(self):
        valid={'watertight':True,'winding_consistent':True,'outer_shells':1,
               'internal_void_shells':0,'signed_volume_mm3':1}
        self.assertTrue(surface_acceptable(valid))
        for key,value in [('winding_consistent',False),('signed_volume_mm3',-1),('outer_shells',2)]:
            self.assertFalse(surface_acceptable({**valid,key:value}))
    def test_complete_component_partition(self):
        self.assertEqual(validate_binary_stl(sample(), [
            {'component_id': 'duct', 'first_triangle': 0, 'triangle_count': 1}]), 1)

    def test_corrupt_stl_is_rejected(self):
        for data in (b'', bytes(84), sample()[:-1], sample()+b'x'):
            with self.assertRaises(ValueError):
                validate_binary_stl(data)
        for offset in (84, 96):  # Both normal and vertex values must be finite.
            data = bytearray(sample())
            struct.pack_into('<f', data, offset, math.nan)
            with self.assertRaises(ValueError):
                validate_binary_stl(data)

    def test_manifest_must_partition_mesh_with_unique_ids(self):
        good = {'component_id': 'duct', 'first_triangle': 0, 'triangle_count': 1}
        for bodies in ([], [good, good], [{**good, 'first_triangle': 1}],
                       [{**good, 'triangle_count': True}], [{**good, 'component_id': ''}]):
            with self.assertRaises(ValueError):
                validate_binary_stl(sample(), bodies)
