import math
import unittest
from dataclasses import replace
from vega.rocket import RocketBrief, design
from vega.orbital_resources import size_orbital_resources


class OrbitalResourceTests(unittest.TestCase):
    def setUp(self):self.brief=RocketBrief(propellant_model='assumed')

    def test_period_and_central_eclipse_against_independent_geometry(self):
        b=self.brief;r=size_orbital_resources(b)
        radius=6371000+b.orbit_altitude_m
        velocity=math.sqrt(3.986004418e14/radius)
        self.assertAlmostEqual(r['orbit']['period_s'],2*math.pi*radius/velocity)
        angle=2*math.asin(6371000/radius)
        self.assertAlmostEqual(r['orbit']['eclipse_s'],angle*radius/velocity)

    def test_delivered_orbital_energy_covers_load_and_battery_losses(self):
        r=size_orbital_resources(self.brief);p=r['power'];a=r['assumptions'];o=r['orbit']
        generated=p['array_area_m2']*1361*a['solar_array_efficiency']*a['solar_eol_factor']*o['sunlight_s']/3600
        required=p['design_load_w']*o['period_s']/3600+p['battery_loss_wh_per_orbit']
        self.assertAlmostEqual(generated,required)
        delivered=p['battery_nominal_energy_wh']*a['battery_depth_of_discharge']*a['battery_discharge_efficiency']
        self.assertAlmostEqual(delivered,p['design_load_w']*o['eclipse_s']/3600)

    def test_load_and_emissivity_control_actual_resource_sizes(self):
        a=size_orbital_resources(self.brief)
        b=size_orbital_resources(replace(self.brief,orbital_electrical_load_w=2000))
        self.assertAlmostEqual(b['power']['array_area_m2'],2*a['power']['array_area_m2'])
        self.assertAlmostEqual(b['thermal']['radiator_area_m2'],2*a['thermal']['radiator_area_m2'])
        low=size_orbital_resources(replace(self.brief,radiator_emissivity=self.brief.radiator_emissivity/2))
        self.assertAlmostEqual(low['thermal']['radiator_area_m2'],2*a['thermal']['radiator_area_m2'])

    def test_zero_load_does_not_invent_resource_mass(self):
        r=size_orbital_resources(replace(self.brief,orbital_electrical_load_w=0))
        self.assertEqual(sum(r['component_masses_kg'].values()),0)
        self.assertTrue(all(r['checks'].values()))

    def test_invalid_thermal_and_efficiency_boundaries_fail(self):
        for changes in ({'radiator_temperature_k':250},{'solar_array_efficiency':0},{'orbital_electrical_load_w':math.nan}):
            with self.assertRaises(ValueError):size_orbital_resources(replace(self.brief,**changes))

    def test_resource_masses_reach_vehicle_mass_and_mission(self):
        a=design(replace(self.brief,vehicle_mass_mode='component_estimate'))['candidates'][0]
        b=design(replace(self.brief,vehicle_mass_mode='component_estimate',orbital_electrical_load_w=2000))['candidates'][0]
        delta=sum(a['orbital_resources']['component_masses_kg'].values())
        self.assertAlmostEqual(b['vehicle_mass_model']['selected_dry_mass_kg']-a['vehicle_mass_model']['selected_dry_mass_kg'],delta*(1+self.brief.vehicle_mass_margin_fraction))
        self.assertLess(b['vehicle_screen']['budget']['available_ideal_delta_v_m_s'],a['vehicle_screen']['budget']['available_ideal_delta_v_m_s'])
