"""Ground-structure, minimum-compliance sizing for Vega's external frame.

This is an axial-bar FE model under explicit representative loads, not a shell
stress, buckling, thermal, fatigue, or fluid-structure validation.  Densities
are optimized on candidate bars; the manufacturable radius floor preserves a
connected material path rather than pretending zero-size bars are printable.
"""
import math
import warnings

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve

SOURCE = 'https://epubs.siam.org/doi/10.1137/0803015'


def optimize_frame(nodes, edges, sectors, max_radius_mm, min_radius_mm,
                   volume_fraction, thrust_n, dynamic_pressure_pa,
                   inlet_area_m2, iterations=30):
    """Minimize summed axial-truss compliance at fixed member volume.

    Last frame ring is fixed. Axial thrust is shared over the first ring and a
    transverse pressure proxy is shared over the middle ring. Neither load
    distribution nor the assumed modulus represents an installed engine test.
    """
    labels = sorted((name for name in nodes if name.startswith('r')),
                    key=lambda name: tuple(int(v) for v in name[1:].split('.')))
    index = {name: i for i, name in enumerate(labels)}
    bars = [(a, b) for a, b in edges if a in index and b in index]
    if len(labels) < 2 * sectors or not bars:
        raise ValueError('Frame optimizer requires at least two complete rings')
    xyz = np.array([nodes[name] for name in labels], dtype=float)
    pairs = np.array([(index[a], index[b]) for a, b in bars], dtype=int)
    delta = xyz[pairs[:, 1]] - xyz[pairs[:, 0]]
    lengths = np.linalg.norm(delta, axis=1)
    if np.any(lengths <= 0) or not np.all(np.isfinite(lengths)):
        raise ValueError('Frame ground structure has invalid bars')
    directions = delta / lengths[:, None]
    maximum_area = math.pi * max_radius_mm**2
    minimum_density = (min_radius_mm / max_radius_mm)**2
    if not 0 < minimum_density < volume_fraction <= 1:
        raise ValueError('Frame volume fraction must exceed the manufacturable radius floor')
    bar_volume = maximum_area * lengths
    target_volume = volume_fraction * bar_volume.sum()
    last_ring = max(int(name.split('.')[0][1:]) for name in labels)
    fixed = {index[name] for name in labels if int(name.split('.')[0][1:]) == last_ring}
    free = [3*i+d for i in range(len(labels)) if i not in fixed for d in range(3)]
    free_index = {dof: i for i, dof in enumerate(free)}
    first = [index[name] for name in labels if name.startswith('r0.')]
    middle_ring = last_ring // 2
    middle = [index[name] for name in labels if name.startswith(f'r{middle_ring}.')]
    axial = np.zeros(3*len(labels)); transverse = np.zeros_like(axial)
    for i in first:
        axial[3*i+2] = thrust_n / len(first)
    side_load = max(.1*thrust_n, .05*dynamic_pressure_pa*inlet_area_m2)
    for i in middle:
        transverse[3*i+1] = side_load / len(middle)
    forces = np.column_stack((axial[free], transverse[free]))
    e_assumed_n_mm2 = 70000.0
    # Cross-sectional area maps directly to the exported circular beam. A
    # SIMP penalty would make reported stiffness disagree with that geometry.
    penalty = 1.0
    dofs = np.array([[3*a, 3*a+1, 3*a+2, 3*b, 3*b+1, 3*b+2]
                     for a, b in pairs])
    signed = np.column_stack((-directions, directions))
    reduced = np.array([[free_index.get(int(d), -1) for d in row] for row in dofs])

    def analysis(densities):
        rows = []; cols = []; values = []
        stiffness = e_assumed_n_mm2 * maximum_area * densities**penalty / lengths
        for bar, vector, k in zip(reduced, signed, stiffness):
            valid = [(int(d), float(v)) for d, v in zip(bar, vector) if d >= 0]
            for row, v1 in valid:
                for col, v2 in valid:
                    rows.append(row); cols.append(col); values.append(k*v1*v2)
        matrix = coo_matrix((values, (rows, cols)), shape=(len(free), len(free))).tocsr()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', MatrixRankWarning)
                displacements = spsolve(matrix, forces)
        except MatrixRankWarning as error:
            raise ValueError('Frame ground structure is singular for its load cases') from error
        if not np.all(np.isfinite(displacements)):
            raise ValueError('Frame ground structure is singular for its load cases')
        full = np.zeros((3*len(labels), 2)); full[free] = displacements
        extensions = np.einsum('ij,ijk->ik', signed, full[dofs])
        compliance = float(np.sum(forces*displacements))
        sensitivity = -penalty * e_assumed_n_mm2 * maximum_area / lengths * densities**(penalty-1) * np.sum(extensions**2, axis=1)
        return compliance, sensitivity, full

    densities = np.full(len(bars), volume_fraction)
    baseline, _, _ = analysis(densities)
    for step in range(iterations):
        _, sensitivity, _ = analysis(densities)
        lower, upper = 1e-20, max(1.0, float(np.max(-sensitivity/bar_volume))) * 1e6
        for _ in range(45):
            lagrange = (lower+upper)/2
            proposed = np.clip(densities*np.sqrt(np.maximum(0, -sensitivity)/(lagrange*bar_volume)),
                               np.maximum(minimum_density, densities-.15),
                               np.minimum(1.0, densities+.15))
            if np.dot(proposed, bar_volume) > target_volume:
                lower = lagrange
            else:
                upper = lagrange
        change = float(np.max(np.abs(proposed-densities)))
        densities = proposed
        if change < 2e-3:
            break
    optimized, _, displacement = analysis(densities)
    if optimized > baseline*(1+1e-6):
        raise ValueError('Frame optimization failed to improve the uniform-volume baseline')
    # Candidate bars at the radius floor may be removed if the remaining
    # ground structure is stable and still beats a uniform frame at the same
    # *actual* material volume. This changes graph topology as well as size.
    active = densities.copy()
    floor_bars = densities <= minimum_density + .005
    if np.any(floor_bars):
        candidate = densities.copy(); candidate[floor_bars] = 0
        try:
            candidate_compliance, _, candidate_displacement = analysis(candidate)
            candidate_fraction = float(np.dot(candidate, bar_volume)/bar_volume.sum())
            comparison, _, _ = analysis(np.full(len(bars), candidate_fraction))
            if candidate_compliance <= comparison and candidate_compliance <= optimized*1.15:
                active = candidate
                optimized = candidate_compliance
                displacement = candidate_displacement
        except ValueError:
            pass
    actual_fraction = float(np.dot(active,bar_volume)/bar_volume.sum())
    same_volume_baseline, _, _ = analysis(np.full(len(bars), actual_fraction))
    active_keys = [f'{a}|{b}' for (a,b),x in zip(bars,active) if x>0]
    return {
        'status': 'conditional_ground_structure_optimized',
        'method': 'Ground-structure bar-area optimization, axial-bar finite elements, optimality-criteria volume update',
        'source': SOURCE,
        'edge_radii_mm': {f'{a}|{b}': float(max_radius_mm*math.sqrt(x)) for (a,b),x in zip(bars,active) if x>0},
        'edge_density': {f'{a}|{b}': float(x) for (a,b),x in zip(bars,active)},
        'candidate_member_count': len(bars),
        'selected_member_count': len(active_keys),
        'removed_members': [f'{a}|{b}' for (a,b),x in zip(bars,active) if x==0],
        'iteration_count': step+1,
        'volume_fraction_target': volume_fraction,
        'volume_fraction_actual': actual_fraction,
        'baseline_uniform_compliance_n_mm': same_volume_baseline,
        'optimized_compliance_n_mm': optimized,
        'compliance_improvement_fraction': 1-optimized/same_volume_baseline,
        'maximum_displacement_mm': float(np.max(np.linalg.norm(displacement.reshape(len(labels),3,2),axis=1))),
        'load_cases_n': {'axial_total': thrust_n, 'transverse_total': side_load},
        'boundary': f'Last ring r{last_ring} fixed in translation; ring nodes form the axial-bar ground structure.',
        'assumed_elastic_modulus_n_mm2': e_assumed_n_mm2,
        'minimum_radius_mm': min_radius_mm,
        'limits': 'Representative axial and lateral loads; assumed isotropic modulus. Bar axial compliance only. No pressure-shell stress, joint stiffness, beam bending, buckling, fatigue, thermal stress, dynamic response, or physical validation.'}
