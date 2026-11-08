import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from vega.meshing.cad import cad_duct
from vega.meshing.hybrid import build_hybrid,axial_grid,audit_volume,write_msh,inspection_scene
from vega.meshing.quality import audit_triangle_quality
from vega_geometry.topology import mesh_topology


def sections():
    return [dict(z_mm=z,width_mm=w,height_mm=20.,wall_mm=2.,
                 lobe_amplitude=.04,lobe_count=3,twist_rad=.1*z/50) for z,w in [(0.,30.),(25.,25.),(50.,35.)]]


class MeshingBackendTests(unittest.TestCase):
    def test_cad_backend_is_closed_and_quality_responds_to_size(self):
        coarse=cad_duct(sections(),5.,.2)
        fine=cad_duct(sections(),2.5,.1)
        for mesh in (coarse,fine):
            audit=mesh_topology(mesh)
            self.assertTrue(audit['closed_manifold']);self.assertTrue(audit['winding_consistent'])
            self.assertGreater(audit['signed_volume_mm3'],0)
            self.assertGreater(mesh['tessellation']['triangle_quality']['mean'],.7)
        self.assertGreater(len(fine['triangles']),len(coarse['triangles']))
        again=cad_duct(sections(),5.,.2);again['vertices'][0][0]+=1
        self.assertNotEqual(again['vertices'],coarse['vertices'])

    def test_rectangular_cad_uses_new_backend(self):
        shape=cad_duct(sections(),5.,.2,'rectangular')
        self.assertTrue(mesh_topology(shape)['winding_consistent'])
        self.assertIn('Gmsh',shape['generator'])

    def test_hybrid_is_conforming_positive_and_has_real_mixed_cells(self):
        m=build_hybrid(sections(),8.,sectors=32,layers=4)
        self.assertGreater(len(m.cells[5]),0);self.assertGreater(len(m.cells[6]),0)
        self.assertEqual(m.summary['inverted_cells'],0)
        self.assertTrue(m.summary['conforming_interface'])
        self.assertLessEqual(m.summary['max_axial_growth'],1.3+1e-10)
        self.assertGreater(m.summary['scaled_jacobian']['minimum'],.5)
        scene=inspection_scene(m)
        self.assertEqual(sum(b['triangle_count'] for b in scene['bodies']),len(scene['triangles']))
        self.assertEqual(len(scene['vertices']),len(m.nodes))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'mesh.msh';write_msh(m,p);text=p.read_text()
            for name in ('inlet','outlet','wall','fluid'):self.assertIn('"'+name+'"',text)

    def test_adaptation_increases_cells_and_preserves_geometry_stations(self):
        s=sections();coarse=axial_grid(s,10.);fine=axial_grid(s,10.,indicators=[1.,.2])
        self.assertGreater(len(fine),len(coarse))
        for station in s:self.assertIn(station['z_mm'],fine)
        a=build_hybrid(s,10.,sectors=24,layers=3)
        b=build_hybrid(s,10.,sectors=24,layers=3,indicators=[1.,.2])
        self.assertGreater(b.summary['cells'],a.summary['cells'])
        self.assertAlmostEqual(a.nodes[:,2].min(),b.nodes[:,2].min())
        self.assertAlmostEqual(a.nodes[:,2].max(),b.nodes[:,2].max())

    def test_volume_matches_analytic_straight_cylinder(self):
        s=[dict(z_mm=z,width_mm=20.,height_mm=20.,wall_mm=2.) for z in (0.,40.)]
        m=build_hybrid(s,10.,sectors=48,layers=4)
        self.assertAlmostEqual(m.summary['volume_mm3']/(np.pi*100*40),1,delta=.005)

    def test_invalid_and_inverted_cells_are_rejected(self):
        with self.assertRaises(ValueError):build_hybrid(sections(),-1)
        with self.assertRaisesRegex(ValueError,'budget'):build_hybrid(sections(),1.,max_cells=100)
        with self.assertRaises(ValueError):axial_grid(sections(),10.,indicators=[float('nan'),1])
        nodes=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[1,0,1],[0,1,1]],float)
        with self.assertRaisesRegex(ValueError,'inverted'):audit_volume(nodes,{6:np.array([[0,2,1,3,5,4]])})

    def test_triangle_metric_has_correct_normalization(self):
        q=audit_triangle_quality([[0,0,0],[1,0,0],[.5,np.sqrt(3)/2,0]],[[0,1,2]])
        self.assertAlmostEqual(q['minimum'],1.)


if __name__=='__main__':unittest.main()
