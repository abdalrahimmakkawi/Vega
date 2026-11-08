"""Small disk index for saved studies; avoids reparsing large native run JSONs."""
from pathlib import Path
import json
import re
import threading

_LOCK = threading.Lock()
_ID = re.compile(r'[a-f0-9]{32}\Z')


def run_summaries(data):
    data = Path(data)
    index = data / 'run_index.json'
    with _LOCK:
        try:
            cached = json.loads(index.read_text())
            if not isinstance(cached, dict):
                cached = {}
        except (OSError, ValueError):
            cached = {}
        next_index = {}
        for path in data.glob('*.json'):
            if not _ID.fullmatch(path.stem):
                continue
            stat = path.stat()
            old = cached.get(path.stem, {})
            if old.get('mtime_ns') == stat.st_mtime_ns and old.get('size') == stat.st_size:
                summary = old.get('summary')
            else:
                run = json.loads(path.read_text())
                if run.get('kind') not in ('rocket', 'spacecraft'):
                    continue
                req = run.get('requirements', {})
                summary = {'id': run['id'], 'created_at': run['created_at'],
                    'jacket_pattern': req.get('jacket_pattern', 'unknown'),
                    'nozzle_contour': req.get('nozzle_contour', 'conical'),
                    'propulsion_family': req.get('propulsion_family', 'rocket_only'),
                    'thrust_n': req.get('thrust_n'),
                    'channel_variant': run.get('candidates', [{}])[0].get('engineering', {}).get('channel_count')}
            if summary:
                next_index[path.stem] = {'mtime_ns': stat.st_mtime_ns, 'size': stat.st_size,
                    'summary': summary}
        if next_index != cached:
            temporary = index.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(next_index, separators=(',', ':')))
            temporary.replace(index)
        return [v['summary'] for v in sorted(next_index.values(),
                key=lambda item: item['mtime_ns'], reverse=True)]
