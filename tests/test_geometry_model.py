import unittest
from dataclasses import replace
from vega.rocket import RocketBrief, design
from vega.inlet import normal_shock
from vega.geometry_audit import inspect
from copy import deepcopy


class GeometryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief=RocketBrief(propellant_model='assumed')
        cls.base=design(cls.brief)['candidates'][0]

    def test_layout_moves_tank_and_reroutes_without_changing_capacity(self):
        paired=design(replace(self.brief,tank_layout='paired'))['candidates'][0]
        a,b=self.base,paired
        self.assertNotEqual(a['geometry_model']['recipe_sha256'],b['geometry_model']['recipe_sha256'])
        self.assertTrue(a['geometry_audit']['pass'] and b['geometry_audit']['pass'])
        for ta,tb in zip(a['geometry']['systems']['tanks'],b['geometry']['systems']['tanks']):
            self.assertEqual(ta['length_mm'],tb['length_mm'])
            self.assertEqual(ta['radius_mm'],tb['radius_mm'])
        self.assertNotEqual(a['geometry']['systems']['tanks'][0]['center'],b['geometry']['systems']['tanks'][0]['center'])
        self.assertGreater(a['engineering']['feed_route_lengths_m']['fuel'],b['engineering']['feed_route_lengths_m']['fuel'])
        self.assertGreater(a['engineering']['pressure_bar']['fuel_feed_loss'],b['engineering']['pressure_bar']['fuel_feed_loss'])

    def test_clearance_changes_recipe_and_pressure_screen(self):
        wide=design(replace(self.brief,tank_clearance_mm=40))['candidates'][0]
        self.assertGreater(wide['dimensions']['diameter_mm'],self.base['dimensions']['diameter_mm'])
        self.assertGreater(wide['engineering']['pressure_bar']['fuel_feed_loss'],self.base['engineering']['pressure_bar']['fuel_feed_loss'])
        self.assertTrue(all(wide['geometry_model']['checks'].values()))

    def test_no_cooling_still_connects_directly_to_injector(self):
        c=design(replace(self.brief,cooling_passages=0))['candidates'][0]
        self.assertTrue(c['geometry_audit']['pass'])
        ids={x['id'] for x in c['geometry_model']['components']}
        self.assertNotIn('cooling_channels',ids)
        self.assertEqual(len(c['geometry']['systems']['manifolds']),2)

    def test_audit_rejects_cooling_bypass_even_with_same_fluid(self):
        recipe=deepcopy(self.base['geometry'])
        feed,_,returned=recipe['systems']['manifolds']
        returned['bore_points'][1]=feed['bore_points'][1]
        result=inspect(recipe)
        self.assertFalse(result['checks']['no_feed_return_short_circuit'])
        self.assertFalse(result['pass'])

    def test_normal_shock_reference_and_conservation(self):
        s=normal_shock(2)
        self.assertAlmostEqual(s['mach'],1/(3**.5))
        self.assertAlmostEqual(s['pressure_ratio'],4.5)
        self.assertAlmostEqual(s['density_ratio'],8/3)
        self.assertAlmostEqual(s['total_pressure_ratio'],.7208738615,places=9)
        self.assertEqual(normal_shock(1)['total_pressure_ratio'],1)
        # Mass, momentum and stagnation enthalpy across a Mach 2 normal shock.
        rho,p,g=1,1,1.4
        u=2*g**.5;rho2=rho*s['density_ratio'];p2=p*s['pressure_ratio'];u2=rho*u/rho2
        self.assertAlmostEqual(p+rho*u*u,p2+rho2*u2*u2)
        self.assertAlmostEqual(g/(g-1)*p/rho+u*u/2,g/(g-1)*p2/rho2+u2*u2/2)

    def test_flow_area_drives_own_mesh_without_inventing_net_thrust(self):
        a=self.base['vehicle_screen']['inlet_reference']
        b=design(replace(self.brief,inlet_capture_area_m2=2*self.brief.inlet_capture_area_m2))['candidates'][0]['vehicle_screen']['inlet_reference']
        self.assertLess(a['relative_mass_residual'],1e-12)
        self.assertNotEqual(a['geometry_sha256'],b['geometry_sha256'])
        self.assertAlmostEqual(b['mass_flow_kg_s'],2*a['mass_flow_kg_s'])
        self.assertAlmostEqual(a['stations'][0]['area_m2'],self.brief.inlet_capture_area_m2)
        self.assertIsNone(b['net_thrust_n'])
        self.assertIn('Gmsh',b['mesh']['generator'])
        # Recover the first inner CAD boundary independently of node numbering.
        import math
        first=a['stations'][0];w,h=first['width_mm']/2,first['height_mm']/2
        ring=[p for p in a['mesh']['vertices'] if abs(p[2]-first['z_mm'])<1e-8
              and abs((p[0]/w)**2+(p[1]/h)**2-1)<1e-4]
        ring.sort(key=lambda p:math.atan2(p[1]/h,p[0]/w))
        self.assertGreater(len(ring),20)
        area=abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(ring,ring[1:]+ring[:1])))/2e6
        self.assertAlmostEqual(area,self.brief.inlet_capture_area_m2,delta=.003*self.brief.inlet_capture_area_m2)
        rect=design(replace(self.brief,inlet_section='rectangular'))['candidates'][0]['vehicle_screen']['inlet_reference']
        self.assertEqual(rect['mass_flow_kg_s'],a['mass_flow_kg_s'])
        self.assertNotEqual(rect['geometry_sha256'],a['geometry_sha256'])

    def test_high_temperature_fails_reference_domain_without_fake_mesh(self):
        c=design(replace(self.brief,transition_mach=8))['candidates'][0]
        r=c['vehicle_screen']['inlet_reference']
        self.assertEqual(r['status'],'outside_reference_domain')
        self.assertIsNone(r['mesh'])


if __name__=='__main__':
    unittest.main()
