import unittest
from collections import Counter
from vega_geometry import Assembly, Port, centerline_length, fingerprint
from vega_geometry.loft import rectangular_duct, elliptical_duct
from math import sin, pi


class GeometryTests(unittest.TestCase):
    def test_route_uses_registered_positions_and_rejects_mixed_media(self):
        a=Assembly()
        a.component('source','vessel');a.component('target','vessel')
        a.port(Port('s','source','water',(0,0,0),2))
        a.port(Port('t','target','water',(10,0,10),2))
        route=a.route('line','Line','water','s','t',[[10,0,0]],2)
        self.assertEqual(centerline_length(route['bore_points']),20)
        self.assertEqual(len(a.export()['connections']),2)
        with self.assertRaises(ValueError): a.route('bad','Bad','air','s','t',[],2)
        with self.assertRaises(ValueError): a.component('source','vessel')

    def test_coincident_interfaces_and_invalid_route(self):
        a=Assembly()
        a.component('a','test');a.component('b','test')
        a.port(Port('a.out','a','water',(0,0,0),2))
        a.port(Port('b.in','b','water',(0,0,1),2))
        with self.assertRaises(ValueError): a.connect('a.out','b.in')
        with self.assertRaises(ValueError): a.route('bad','Bad','water','a.out','b.in',[],-1)
        self.assertNotIn('bad',a.components)
        for radius in (0,-1,True,float('nan')):
            with self.assertRaises(ValueError): Port('x','a','water',(0,0,0),radius)
        with self.assertRaises(ValueError): centerline_length([(0,0,0),(0,0,0)])

    def test_hash_is_order_independent_and_rejects_nan(self):
        self.assertEqual(fingerprint({'a':1,'b':2}),fingerprint({'b':2,'a':1}))
        self.assertNotEqual(fingerprint({'a':1}),fingerprint({'a':2}))
        with self.assertRaises(ValueError): fingerprint({'a':float('nan')})

    def test_duct_is_closed_material_with_open_flow_and_positive_volume(self):
        mesh=rectangular_duct([{'z_mm':0,'width_mm':10,'height_mm':6},
                               {'z_mm':20,'width_mm':10,'height_mm':6}],1)
        directed=Counter((t[i],t[(i+1)%3]) for t in mesh['triangles'] for i in range(3))
        self.assertTrue(all(count==1 and directed[(b,a)]==1 for (a,b),count in directed.items()))
        volume=0
        for t in mesh['triangles']:
            a,b,c=[mesh['vertices'][i] for i in t]
            cross=(b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0])
            volume+=sum(x*y for x,y in zip(a,cross))/6
        self.assertAlmostEqual(volume,(12*8-10*6)*20)
        # Every end face belongs to the annular rim, never the central opening.
        for t in mesh['triangles']:
            p=[mesh['vertices'][i] for i in t]
            if len({v[2] for v in p})==1:
                x,y=[sum(v[i] for v in p)/3 for i in (0,1)]
                self.assertTrue(abs(x)>=5 or abs(y)>=3)

    def test_loft_rejects_collapsed_or_reversed_stations(self):
        for second in ({'z_mm':0,'width_mm':1,'height_mm':1},
                       {'z_mm':1,'width_mm':0,'height_mm':1}):
            with self.assertRaises(ValueError):
                rectangular_duct([{'z_mm':0,'width_mm':1,'height_mm':1},second],1)

    def test_elliptical_duct_manifold_and_known_polygon_volume(self):
        mesh=elliptical_duct([{'z_mm':0,'width_mm':10,'height_mm':6},
                              {'z_mm':20,'width_mm':10,'height_mm':6}],1)
        directed=Counter((t[i],t[(i+1)%3]) for t in mesh['triangles'] for i in range(3))
        self.assertTrue(all(count==1 and directed[(b,a)]==1 for (a,b),count in directed.items()))
        volume=0
        for t in mesh['triangles']:
            a,b,c=[mesh['vertices'][i] for i in t]
            volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        self.assertAlmostEqual(volume,(6*4-5*3)*96*sin(2*pi/96)/2*20)


if __name__=='__main__':
    unittest.main()
