"""Measured mesh quality; surface quality never stands in for a volume audit."""
import numpy as np


def audit_triangle_quality(nodes, elements):
    p = np.asarray(nodes, float)[np.asarray(elements, np.int64)]
    edges = np.stack([np.linalg.norm(p[:, (i+1)%3]-p[:, i], axis=1) for i in range(3)], axis=1)
    area2 = np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1)
    if not len(p) or not np.isfinite(p).all() or np.any(area2 <= 1e-14*edges.max(axis=1)**2):
        raise ValueError('Empty, nonfinite or degenerate surface mesh')
    q = np.clip(4*area2**2/(edges.sum(axis=1)*edges.prod(axis=1)), 0, 1)
    return {'metric': '2*inradius/circumradius', 'minimum': float(q.min()),
            'p05': float(np.quantile(q, .05)), 'median': float(np.median(q)),
            'mean': float(q.mean()), 'maximum': float(q.max()),
            'below_0_2': int(np.sum(q < .2)), 'triangles': len(q)}
