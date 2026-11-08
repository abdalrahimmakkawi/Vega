import unittest
from vega_geometry.topology import graph_topology, mesh_topology, reachable
from vega_geometry.beam import beam
from vega_geometry.loft import elliptical_duct


class TopologyTests(unittest.TestCase):
    def test_closed_cylinder_and_annular_duct_have_different_genus(self):
        solid=mesh_topology(beam([0,0,0],[2,3,12],1))
        duct=mesh_topology(elliptical_duct([
            {'z_mm':0,'width_mm':10,'height_mm':8},
            {'z_mm':20,'width_mm':12,'height_mm':10}],1))
        for audit in (solid,duct):
            self.assertTrue(audit['closed_manifold'])
            self.assertTrue(audit['winding_consistent'])
            self.assertGreater(audit['signed_volume_mm3'],0)
        self.assertEqual((solid['euler_characteristic'],solid['total_genus']),(2,0))
        self.assertEqual((duct['euler_characteristic'],duct['total_genus']),(0,1))

    def test_missing_face_and_reversed_face_are_detected(self):
        shape=beam([0,0,0],[0,0,10],1)
        shape['triangles'][0].reverse()
        self.assertFalse(mesh_topology(shape)['winding_consistent'])
        shape['triangles'].pop()
        audit=mesh_topology(shape)
        self.assertFalse(audit['closed_manifold'])
        self.assertEqual(audit['boundary_edges'],3)

    def test_pinched_vertex_is_not_a_manifold(self):
        tetra={'vertices':[[0,0,0],[1,0,0],[0,1,0],[0,0,1]],
               'triangles':[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]}
        tetra['vertices'] += [[-1,0,0],[0,-1,0],[0,0,-1]]
        tetra['triangles'] += [[0,4,5],[0,6,4],[0,5,6],[4,6,5]]
        audit=mesh_topology(tetra)
        self.assertEqual(audit['nonmanifold_edges'],0)
        self.assertEqual(audit['nonmanifold_vertices'],1)
        self.assertFalse(audit['closed_manifold'])

    def test_graph_cycles_and_direction(self):
        edges=[('a','b'),('b','c'),('a','c')]
        audit=graph_topology(['a','b','c','d'],edges)
        self.assertEqual(audit['cycle_rank'],1)
        self.assertEqual(audit['connected_components'],2)
        self.assertEqual(audit['isolated_nodes'],['d'])
        self.assertTrue(reachable(edges,'a','c'))
        self.assertFalse(reachable(edges,'c','a'))
        with self.assertRaises(ValueError):graph_topology(['a','b'],[('a','b'),('b','a')])
        with self.assertRaises(ValueError):beam([0,0,0],[0,0,0],1)
