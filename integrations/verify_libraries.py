"""Run every native library branch and check emitted geometry/provenance."""
import json
import math
from pathlib import Path
import struct
import sys
import uuid
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from vega.rocket import RocketBrief

results=[]
for pattern in ('none','bcc','quasi','penrose'):
    identity=uuid.uuid4().hex
    server.run_job(identity,replace(RocketBrief(),jacket_pattern=pattern))
    job=server.JOBS[identity]
    if job['status']!='complete':raise RuntimeError(job)
    run=server.read_run(identity)
    path=server.DATA/'native'/f'{identity}.stl'
    triangles=list(struct.iter_unpack('<12fH',path.read_bytes()[84:]))
    assert all(all(math.isfinite(v) for v in t[:12]) for t in triangles)
    checks=json.loads(Path(str(path)+'.checks.json').read_text())
    assert sum(b['triangle_count'] for b in checks['bodies'])==len(triangles)
    names={x['library'] for x in checks['library_execution']}
    assert {'ShapeKernel','PicoGK'}<=names
    expected={'bcc':'LatticeLibrary','quasi':'QuasiCrystals','penrose':'QuasiCrystals / PenrosePattern'}
    if pattern!='none':
        assert expected[pattern] in names
        body=checks['bodies'][-1];assert body['component_id']=='jacket'
        jt=triangles[body['first_triangle']:]
        radii=[math.hypot(t[k],t[k+1]) for t in jt for k in (3,6,9)]
        recipe=run['candidates'][0]['geometry']['jacket']
        assert min(radii)>recipe['inner_radius_mm']-1.5
        assert max(radii)<recipe['outer_radius_mm']+1.5
    assert run['artifact'] and not run['artifact']['engineering_validated']
    results.append({'pattern':pattern,'run_id':identity,'triangles':len(triangles),'calls':checks['library_execution']})
    print(pattern,len(triangles),identity,flush=True)
assert len({r['triangles'] for r in results})==4
(server.DATA/'library-smoke-evidence.json').write_text(json.dumps(results,indent=2))
