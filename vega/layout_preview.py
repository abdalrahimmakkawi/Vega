"""Compose a review STL from a saved single-layer layout and a sized precooler."""
import json
import shutil
import struct
import sys
from pathlib import Path

from .artifacts import artifact_digest, open_artifact


def compose(layout, part, output):
    def verified(folder, name):
        path = folder / name
        manifest = json.loads((folder / 'manifest.json').read_text())
        if artifact_digest(path) != manifest[name]:
            raise ValueError(f'Changed input: {path}')
        return path

    report = json.loads(verified(layout, 'report.json').read_text(encoding='utf-8'))
    if report.get('scene_layers') or report.get('scene_extension'):
        raise ValueError('Expected a packed single-layer scene')
    scene = verified(layout, 'scene.stl')
    hidden = set(report.get('hidden_component_ids', []))
    with open_artifact(scene) as original, open_artifact(part) as replacement:
        original.seek(80)
        original_count, = struct.unpack('<I', original.read(4))
        replacement.seek(80)
        new_count, = struct.unpack('<I', replacement.read(4))
        bodies = report['bodies']
        if sum(b['component_id'] == 'precooler' for b in bodies) != 1:
            raise ValueError('Expected one precooler body')
        total = 0
        cursor = 0
        for body in bodies:
            if body['first_triangle'] != cursor:
                raise ValueError('Invalid packed body ranges')
            cursor += body['triangle_count']
            if body['component_id'] not in hidden:
                total += new_count if body['component_id'] == 'precooler' else body['triangle_count']
        if cursor != original_count:
            raise ValueError('Incomplete body inventory')
        with output.open('xb') as dst:
            dst.write(b'Vega layout review, millimetres, assembly fit unverified'.ljust(80, b' '))
            dst.write(struct.pack('<I', total))
            for body in bodies:
                if body['component_id'] in hidden:
                    continue
                if body['component_id'] == 'precooler':
                    shutil.copyfileobj(replacement, dst)
                    continue
                original.seek(84 + body['first_triangle'] * 50)
                remaining = body['triangle_count'] * 50
                while remaining:
                    chunk = original.read(min(remaining, 1024*1024))
                    if not chunk:
                        raise ValueError('Truncated source mesh')
                    dst.write(chunk)
                    remaining -= len(chunk)
            if dst.tell() != 84 + total * 50:
                raise ValueError('Invalid review mesh size')
    return total


if __name__ == '__main__':
    print(compose(*(Path(arg) for arg in sys.argv[1:])), 'triangles')
