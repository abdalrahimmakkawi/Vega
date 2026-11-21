import unittest
from math import sqrt
from vega.demonstrator import recipe
from vega.propulsion import combust,nozzle,helium_loop,bench_study
from vega.transitions import assess_transition


class BenchPhysicsTests(unittest.TestCase):
    def test_cooling_network_rejects_detached_branch_and_port(self):
        from copy import deepcopy
        from vega.cooling import validate_network
        cooling=recipe()['cooling']
        self.assertLess(cooling['network']['maximum_junction_gap_mm'],.05)
        for group in ('routes','ports'):
            bad=deepcopy(cooling)
            bad[group][0]['points'][0][0]+=5
            with self.assertRaises(ValueError):
                validate_network(bad['routes'],bad['collectors'],bad['ports'])

    def test_smooth_throat_preserves_area_ratio_in_all_cases(self):
        for flow in (3.5,4.,4.5):
            r=recipe({'reference_flow_g_s':flow})
            radii=[row['radii_mm'][0] for row in r['core']]
            self.assertEqual(radii.index(min(radii)),98-66)
            self.assertAlmostEqual(min(radii),3.5)
            self.assertLess(abs(radii[32]-radii[31]),.06)
            self.assertLess(abs(radii[33]-radii[32]),.06)
            self.assertAlmostEqual((radii[-1]/min(radii))**2,r['nozzle_geometry']['expansion_ratio'])

    def test_combustion_conserves_elements_and_enthalpy(self):
        for medium,fuel in [('air',.000116),('oxygen',.0005)]:
            c=combust(.004,fuel,600000,500,oxidizer=medium)
            self.assertTrue(c['converged'])
            self.assertLess(c['element_mass_fraction_error'],1e-8)
            self.assertLess(abs(c['energy_residual_w']),.001)
            self.assertAlmostEqual(sum(c['composition'].values()),1,places=8)
            self.assertAlmostEqual(c['mass_flow_kg_s'],.004+fuel)

    def test_heat_extraction_reduces_combustion_temperature(self):
        adiabatic=combust(.004,.000116,600000,500)
        cooled=combust(.004,.000116,600000,500,heat_removed_w=1000)
        self.assertLess(cooled['temperature_k'],adiabatic['temperature_k'])
        self.assertLess(abs(cooled['energy_residual_w']),.001)
        with self.assertRaises(ValueError):combust(.004,.000116,600000,25)

    def test_nozzle_matches_choked_mass_flow_and_pressure_thrust(self):
        c=dict(gamma=1.4,gas_constant_j_kgk=287.,temperature_k=1000.,pressure_pa=1e6,mass_flow_kg_s=1.)
        n=nozzle(c,2.,101325.)
        recovered=n['throat_area_m2']*c['pressure_pa']/sqrt(c['temperature_k'])*sqrt(1.4/287)*(2/2.4)**3
        self.assertAlmostEqual(recovered,1.)
        vacuumish=nozzle(c,2.,1000.)
        self.assertAlmostEqual(vacuumish['net_thrust_n']-n['net_thrust_n'],(101325-1000)*n['exit_area_m2'])
        moving=nozzle(c,2.,101325.,intake_mass_kg_s=.8,flight_speed_m_s=100)
        self.assertAlmostEqual(n['net_thrust_n']-moving['net_thrust_n'],80.)
        self.assertIsNone(nozzle(c,2.,900000.)['net_thrust_n'])

    def test_helium_energy_and_shaft_balance(self):
        loop=helium_loop(1000.,100.)
        self.assertLess(abs(loop['shaft_residual_w']),1e-6)
        self.assertLess(abs(loop['loop_energy_residual_w']),1e-6)
        self.assertGreater(loop['circulator_shaft_w'],0)
        self.assertGreater(loop['sink_assumptions']['enthalpy_rise_j_kg'],0)

    def test_closed_subcycles_do_not_claim_a_closed_engine(self):
        c=bench_study(.004)
        self.assertTrue(c['checks']['combustion_energy_closed'])
        self.assertTrue(c['checks']['preburner_HX3_capacity_closed'])
        self.assertFalse(c['checks']['finite_fuel_sink_closed'])
        self.assertFalse(c['whole_engine_closed'])
        self.assertGreater(c['airbreathing']['combustion']['heat_extracted_w'],0)
        chosen=c['nozzle_search']['selected_expansion_ratio']
        candidates=c['nozzle_search']['candidates']
        self.assertEqual(chosen,max(candidates,key=lambda r:r['score'])['expansion_ratio'])

    def test_cooling_routes_and_nozzle_drive_recipe(self):
        r=recipe();cooling=r['cooling']
        self.assertEqual(len(cooling['routes']),4)
        self.assertEqual(len(cooling['ports']),2)
        self.assertEqual(len(cooling['candidates']),12)
        self.assertTrue(cooling['selection']['feasible'])
        self.assertGreaterEqual(cooling['selection']['air_corridor_clearance_mm'],.8)
        self.assertEqual(len(cooling['graph']['connections']),8)
        self.assertAlmostEqual((r['core'][-1]['radii_mm'][0]/3.5)**2,r['nozzle_geometry']['expansion_ratio'])

    def test_transitions_require_explicit_evidence_and_never_certify_flight(self):
        inhibited=assess_transition('airbreathing','rocket',{})
        self.assertEqual(inhibited['status'],'inhibited')
        self.assertIn('engine_cycle_valid',inhibited['missing'])
        evidence={name:True for name in inhibited['missing']}
        result=assess_transition('airbreathing','rocket',evidence)
        self.assertEqual(result['status'],'simulation_guard_satisfied')
        self.assertFalse(result['flight_transition_verified'])
        evidence['engine_cycle_valid']='true'
        self.assertEqual(assess_transition('airbreathing','rocket',evidence)['status'],'inhibited')


if __name__=='__main__':unittest.main()
