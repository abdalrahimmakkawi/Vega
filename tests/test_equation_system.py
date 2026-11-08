import math
import unittest
from unittest.mock import patch

from vega.equation_system import Variable as V, Equation as E, solve_system
from vega.equation_system import EquationConvergenceError
from vega.propulsion_model import nozzle_design, predict_fixed_hardware
from vega.rocket import RocketBrief, design


class EquationSystemTests(unittest.TestCase):
    def test_coupled_analytic_solution_with_different_units_and_scales(self):
        state, report = solve_system('test', [V('p', 'Pa', 1e5, 1e6), V('q', 'kg/s', 1., 1.)],
            [E('pressure_flow', 'Pa', 1e6, lambda s: s['p']-2e6*s['q']),
             E('boundary', 'kg/s', 1., lambda s: s['q']+s['p']/1e6-3)])
        self.assertAlmostEqual(state['q'], 1.)
        self.assertAlmostEqual(state['p'], 2e6, places=4)
        self.assertEqual(report['jacobian_rank'], 2)

    def test_inconsistent_and_singular_models_are_rejected(self):
        for equations in ([E('a', '1', 1., lambda s: s['x']-1), E('b', '1', 1., lambda s: s['x']-2)],
                          [E('a', '1', 1., lambda s: s['x']+s['y']-1), E('b', '1', 1., lambda s: 2*(s['x']+s['y']-1))]):
            with self.assertRaises(ValueError):
                solve_system('bad', [V('x', '1', .1, 1), V('y', '1', .1, 1)], equations)

    def test_nozzle_against_independent_analytic_mach_two_case(self):
        g, r, tc, pc, pa, mach, at = 1.4, 287., 1000., 1e6, 1e4, 2., .001
        factor = 1+(g-1)*mach**2/2
        expansion = (2/(g+1)*factor)**((g+1)/(2*(g-1)))/mach
        te = tc/factor
        pe = pc/factor**(g/(g-1))
        velocity = mach*math.sqrt(g*r*te)
        mdot = at*pc/math.sqrt(tc)*math.sqrt(g/r)*(2/(g+1))**((g+1)/(2*(g-1)))
        force = mdot*velocity+(pe-pa)*expansion*at
        state, report = nozzle_design(force,pc,pa,tc,g,r,expansion)
        self.assertAlmostEqual(state['mach'], mach, places=7)
        self.assertAlmostEqual(state['throat_area'], at, places=10)
        self.assertAlmostEqual(state['mass_flow'], mdot, places=7)
        self.assertLess(report['max_scaled_residual'], 1e-8)

    def test_geometry_consumes_solved_state_and_responds_to_requirement(self):
        runs = [design(RocketBrief.parse({'propellant_model':'assumed','propulsion_family':'rocket_only',
                    'jacket_pattern':'none','cooling_passages':0,'thrust_n':f})) for f in (350,700)]
        a,b = [run['candidates'][0] for run in runs]
        self.assertAlmostEqual(b['performance']['throat_area_m2']/a['performance']['throat_area_m2'],2,places=7)
        self.assertAlmostEqual(min(r for _,r in b['geometry']['profile_mm'])/min(r for _,r in a['geometry']['profile_mm']),math.sqrt(2),places=7)
        for candidate in (a,b):
            eng = candidate['engineering']
            state = eng['equation_solution']['variables']
            self.assertAlmostEqual(eng['injector_screen']['single_fuel_orifice_radius_mm'],math.sqrt(state['fuel_orifice_area']['value']/math.pi)*1000)
            self.assertEqual(eng['equation_solution']['status'],'converged')

    def test_fixed_hardware_responds_to_supply_pressure_without_resizing(self):
        brief = RocketBrief.parse({'propellant_model':'assumed','propulsion_family':'rocket_only','jacket_pattern':'none'})
        candidate = design(brief)['candidates'][0]
        low = predict_fixed_hardware(brief,candidate['performance'],candidate['engineering'],3e6)
        high = predict_fixed_hardware(brief,candidate['performance'],candidate['engineering'],4e6)
        for variable in ('chamber_pressure','fuel_flow','oxidizer_flow'):
            self.assertGreater(high['variables'][variable]['value'],low['variables'][variable]['value'])
        self.assertEqual(low['boundary_conditions']['throat_area_m2'],high['boundary_conditions']['throat_area_m2'])
        self.assertLess(high['max_scaled_residual'],1e-8)

    def test_operating_point_matches_quadratic_pressure_solution(self):
        brief = RocketBrief(propellant_model='assumed',propulsion_family='rocket_only',
                            chamber_pressure_bar=20,tank_pressure_bar=30,cooling_passages=0,valve_loss_bar=0)
        pc, drop, supply, rho, cd = 2e6, 4e5, 3e6, 1000., .7
        eng={'properties':{m+'_density_kg_m3':rho for m in ('fuel','oxidizer')},
             'mass_flow_kg_s':{'fuel':1.,'oxidizer':2.},'feed_bore_radius_mm':{'fuel':3.,'oxidizer':3.},
             'feed_route_lengths_m':{'fuel':0.,'oxidizer':0.},
             'injector_screen':{'discharge_coefficient_assumed':cd}}
        for medium, flow in (('fuel',1.),('oxidizer',2.)):
            eng['properties'][medium+'_viscosity_pa_s']=.001
            area=flow/(cd*math.sqrt(2*rho*drop))
            eng['injector_screen']['single_'+medium+'_orifice_radius_mm']=math.sqrt(area/math.pi)*1000
        performance={'mass_flow_kg_s':3.,'throat_area_m2':.001,'chemistry':{'gamma':1.4}}
        with patch('vega.engineering.darcy_loss_bar',return_value=(0.,0.,0.)):
            result=predict_fixed_hardware(brief,performance,eng)
        # p + drop*(p/pc)^2 = supply for equal normalized branch resistance.
        a=drop/pc**2
        expected=2*supply/(1+math.sqrt(1+4*a*supply))
        self.assertAlmostEqual(result['variables']['chamber_pressure']['value'],expected,places=4)
        self.assertAlmostEqual(result['predicted_mixture_ratio'],2.,places=9)

    def test_failed_alternative_does_not_abort_search_or_get_meshed(self):
        def predict(brief,performance,engineering,**kwargs):
            if engineering['channel_count']==12:
                raise EquationConvergenceError('deliberate rejected alternative')
            return predict_fixed_hardware(brief,performance,engineering,**kwargs)
        with patch('vega.rocket.predict_fixed_hardware',side_effect=predict):
            study=design(RocketBrief(propellant_model='assumed',propulsion_family='rocket_only',jacket_pattern='none'))
            rejected=next(v for v in study['alternatives'] if v['channel_count']==12)
            self.assertFalse(rejected['selected'])
            self.assertFalse(rejected['screen_pass'])
            self.assertIn('operating_point_convergence',rejected['failed_checks'])
            with self.assertRaisesRegex(EquationConvergenceError,'Selected channel variant'):
                design(RocketBrief(propellant_model='assumed',propulsion_family='rocket_only',channel_variant=12))


if __name__ == '__main__':
    unittest.main()
