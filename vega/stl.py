"""Shared binary STL boundary checks for native and assembled component scenes."""
import math
import struct


def surface_acceptable(audit):
    return bool(audit.get('watertight') and audit.get('winding_consistent')
                and audit.get('outer_shells') == 1 and audit.get('internal_void_shells') == 0
                and audit.get('signed_volume_mm3', 0) > 0)


def validate_binary_stl(data, bodies=None):
    if len(data) < 84:
        raise ValueError('Truncated STL header')
    count = struct.unpack_from('<I', data, 80)[0]
    if not count or len(data) != 84 + 50*count:
        raise ValueError('Invalid STL triangle count or length')
    for triangle in struct.iter_unpack('<12fH', memoryview(data)[84:]):
        if not all(math.isfinite(value) for value in triangle[:12]):
            raise ValueError('Nonfinite STL normal or vertex')
    if bodies is not None:
        offset = 0
        identities = set()
        for body in bodies:
            identity = body.get('component_id')
            first, size = body.get('first_triangle'), body.get('triangle_count')
            if not isinstance(identity, str) or not identity or identity in identities:
                raise ValueError('Missing or duplicate STL component identity')
            if type(first) is not int or type(size) is not int or first != offset or size <= 0:
                raise ValueError('Missing, overlapping or empty STL component range')
            identities.add(identity)
            offset += size
        if offset != count:
            raise ValueError(f'Component ranges cover {offset} of {count} STL triangles')
    return count
