import unittest
from vega.meshing.airpath import connected_stations, build_airpath
from vega.meshing.hybrid import inspection_scene


class AirpathTests(unittest.TestCase):
    def test_five_stage_assembly_is_continuous_and_positive(self):
        def station(z,amp=0):return {'z_mm':z,'width_mm':30+z/20,
            'height_mm':20+z/40,'wall_mm':2.,'lobe_amplitude':amp,
            'lobe_count':8 if amp else 1,'twist_rad':0.}
        ends=[station(z,.04 if z in (80,120,160) else 0) for z in range(0,201,40)]
        assembly={'sections':[[ends[i],ends[i+1]] for i in range(5)]}
        stations,interfaces=connected_stations(assembly)
        self.assertEqual(len(interfaces),4)
        self.assertEqual(len(stations),6)
        mesh,_=build_airpath(assembly,8.)
        self.assertEqual(mesh.summary['inverted_cells'],0)
        self.assertTrue(mesh.summary['conforming_interface'])
        self.assertGreater(mesh.summary['scaled_jacobian']['minimum'],.8)
        self.assertEqual(mesh.summary['interfaces_z_mm'],interfaces)
        self.assertEqual({body['group'] for body in inspection_scene(mesh)['bodies']},
                         {'fluid_core','wall_layers'})


if __name__=='__main__':unittest.main()
