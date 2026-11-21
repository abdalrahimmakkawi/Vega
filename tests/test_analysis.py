import unittest
from vega.demonstrator import recipe
from vega.analysis import potential_flow, beam_fea, analyze
import numpy as np


class AnalysisTests(unittest.TestCase):
    def test_uniform_annulus_has_uniform_velocity_and_balanced_flux(self):
        result=potential_flow(lambda z:np.full_like(z,2.),lambda z:np.full_like(z,8.),step_mm=.5,z_limits=(0,10))
        velocities=np.array(result['field'])[:,2]
        self.assertLess(np.ptp(velocities),1e-9)
        self.assertLess(result['relative_mass_imbalance'],1e-10)
        expected=.004/1.2/(np.pi*(.008**2-.002**2))
        self.assertAlmostEqual(velocities.mean(),expected,8)

    def test_beam_matches_analytical_cantilever_and_reactions(self):
        result=beam_fea(np.linspace(0,50,11),np.full(10,2.))
        expected=.1*.05**3/(3*2e9*(np.pi*.002**4/4))*1000
        self.assertAlmostEqual(result['tip_displacement_mm'],expected,8)
        self.assertAlmostEqual(result['support_reaction_n'],-.1,8)
        self.assertAlmostEqual(abs(result['support_moment_nm']),.005,8)

    def test_movement_changes_geometry_and_solved_results(self):
        a=analyze(recipe({'centrebody_mm':-4}))
        b=analyze(recipe({'centrebody_mm':4}))
        self.assertNotEqual(a['geometry_recipe_sha256'],b['geometry_recipe_sha256'])
        self.assertNotEqual(a['fea']['tip_displacement_mm'],b['fea']['tip_displacement_mm'])
        self.assertFalse(a['shock_solution'])
