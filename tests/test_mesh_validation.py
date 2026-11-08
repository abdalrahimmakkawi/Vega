import unittest
from unittest.mock import patch
from vega.geometry_model import fingerprint
from vega_geometry.beam import beam
from vega.mesh_validation import inspect_surface, _CACHE
from vega_geometry.topology import mesh_topology


class MeshValidationCacheTests(unittest.TestCase):
    def test_repeated_audits_reuse_content_but_do_not_share_mutable_results(self):
        _CACHE.clear();shape=beam([0,0,0],[0,0,10],1,8)
        with patch('vega.mesh_validation.mesh_topology',wraps=mesh_topology) as audit:
            first=inspect_surface(shape);first[0]['closed_manifold']=False
            second=inspect_surface(shape)
            self.assertTrue(second[0]['closed_manifold']);self.assertEqual(audit.call_count,1)
            shape['vertices'][0][0]+=.001
            inspect_surface(shape);self.assertEqual(audit.call_count,2)
