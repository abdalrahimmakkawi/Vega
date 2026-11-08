import math
import unittest
from dataclasses import replace
from vega.thermal_model import thermal_segment
from vega.rocket import RocketBrief, design


class ThermalTests(unittest.TestCase):
    def test_analytic_solution_and_refinement(self):
        args=(300.,1000.,200.,.2,.3,.004,100.,1000.,5000.)
        result=thermal_segment(*args)
        resistance=1/(1000*.2)+.004/(100*.2)+1/(5000*.3)
        expected=1000-700*math.exp(-1/(resistance*200))
        self.assertAlmostEqual(result['bulk_outlet_k'],expected,places=10)
        temp=300.;heat=0.
        for _ in range(20):
            part=thermal_segment(temp,1000.,200.,.2/20,.3/20,.004,100.,1000.,5000.)
            temp=part['bulk_outlet_k'];heat+=part['heat_w']
        self.assertAlmostEqual(temp,expected,places=10)
        self.assertAlmostEqual(heat,result['heat_w'],places=8)
        self.assertLess(abs(result['energy_residual_w']),1e-8)

    def test_cooling_resistance_changes_heat_and_wall_temperature(self):
        a=thermal_segment(300,1000,200,.2,.3,.004,100,1000,5000)
        b=thermal_segment(300,1000,200,.2,.3,.004,100,1000,500)
        self.assertLess(b['heat_w'],a['heat_w'])
        self.assertGreater(b['hot_wall_peak_k'],a['hot_wall_peak_k'])
        self.assertLess(a['hot_wall_peak_k'],1000)
        with self.assertRaises(ValueError):thermal_segment(300,1000,200,.2,.3,-.004,100,1000,500)

    def test_thermal_model_drives_gates_and_keeps_heat_flux_mode_explicit(self):
        brief=RocketBrief.parse({'propellant_model':'assumed','propulsion_family':'rocket_only','jacket_pattern':'none',
            'thermal_model':'thermal_resistance','channel_variant':8})
        candidate=design(brief)['candidates'][0]
        eng=candidate['engineering'];t=eng['thermal']
        self.assertIsNone(t['assumed_heat_flux_mw_m2'])
        self.assertGreater(t['wall_gradient_peak_k'],0)
        self.assertIn('operating_case',t)
        self.assertLess(abs(t['operating_case']['energy_residual_w']),1e-7)
        # A legacy flux input must not affect the resistance model.
        other=design(replace(brief,design_heat_flux_mw_m2=3))['candidates'][0]['engineering']['thermal']
        self.assertEqual(t['heat_load_w'],other['heat_load_w'])
        self.assertEqual(eng['checks']['estimated_hot_wall_temperature'],t['estimated_hot_wall_k']<=brief.max_wall_temperature_k)


if __name__=='__main__':unittest.main()
