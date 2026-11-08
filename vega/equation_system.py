"""Executable, scaled residual systems. All values at this boundary are SI.

Convergence is numerical verification, never experimental validation.
"""
from dataclasses import dataclass
from pathlib import Path
import math
import sys


class EquationConvergenceError(ValueError):
    """A valid model declaration did not produce an acceptable numerical root."""


@dataclass(frozen=True)
class Variable:
    name: str
    unit: str
    initial: float
    scale: float
    lower: float = -math.inf
    upper: float = math.inf


@dataclass(frozen=True)
class Equation:
    name: str
    unit: str
    scale: float
    residual: object


def solve_system(name, variables, equations, *, tolerance=1e-8, max_evaluations=400, difference_step=None):
    """Solve a square bounded system; reject nonconvergence and rank deficiency.

    Residual functions receive a dictionary of named SI values. Scaling belongs
    to the model declaration, so Pa and kg/s do not compete numerically.
    """
    if len(variables) != len(equations) or not variables:
        raise ValueError('Equation system must be square and nonempty')
    if len({v.name for v in variables}) != len(variables):
        raise ValueError('Duplicate variable name')
    if len({e.name for e in equations}) != len(equations):
        raise ValueError('Duplicate equation name')
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('Tolerance must be positive and finite')
    for v in variables:
        if not math.isfinite(v.initial) or not math.isfinite(v.scale) or v.scale <= 0 or not v.lower < v.initial < v.upper:
            raise ValueError('Invalid variable declaration: '+v.name)
    for e in equations:
        if not math.isfinite(e.scale) or e.scale <= 0:
            raise ValueError('Invalid residual scale: '+e.name)
    dependency = str(Path(__file__).resolve().parents[1]/'.tools'/'python')
    if dependency not in sys.path:
        sys.path.insert(0, dependency)
    import numpy as np
    from scipy.optimize import least_squares
    def unpack(x):
        return {v.name: float(xi*v.scale) for v, xi in zip(variables, x)}
    def residual(x):
        state = unpack(x)
        values = [float(e.residual(state))/e.scale for e in equations]
        if not all(math.isfinite(value) for value in values):
            raise ValueError(name+': nonfinite residual')
        return values
    result = least_squares(residual, [v.initial/v.scale for v in variables],
                           bounds=([v.lower/v.scale for v in variables], [v.upper/v.scale for v in variables]),
                           xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=max_evaluations, diff_step=difference_step)
    maximum = float(np.max(np.abs(result.fun)))
    rank = int(np.linalg.matrix_rank(result.jac))
    if not result.success or maximum > tolerance or rank != len(variables):
        raise EquationConvergenceError(f'{name}: equation solve failed (residual={maximum:.3g}, rank={rank}/{len(variables)})')
    state = unpack(result.x)
    return state, {'name': name, 'status': 'converged', 'solver': 'scipy.optimize.least_squares',
                   'evaluations': int(result.nfev), 'jacobian_rank': rank,
                   'relative_difference_step': difference_step,
                   'max_scaled_residual': maximum, 'tolerance': tolerance,
                   'variables': {v.name: {'value': state[v.name], 'unit': v.unit} for v in variables},
                   'equations': [{'name': e.name, 'residual': float(e.residual(state)), 'unit': e.unit,
                                  'scale': e.scale, 'scaled_residual': float(e.residual(state))/e.scale} for e in equations],
                   'validation': 'unvalidated'}
