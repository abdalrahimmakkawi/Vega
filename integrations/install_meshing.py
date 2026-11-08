"""Install isolated meshing tools; repair pip --target's Windows DLL placement."""
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'.tools/meshing'
subprocess.run([sys.executable,'-m','pip','install','--upgrade','--target',str(target),
                '-r',str(ROOT/'requirements-meshing.txt')],check=True)
if sys.platform=='win32' and not (target/'gmsh-4.15.dll').exists():
    wheels=ROOT/'.tools/downloads';wheels.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,'-m','pip','download','--no-deps','--dest',str(wheels),'gmsh==4.15.2'],check=True)
    with ZipFile(next(wheels.glob('gmsh-4.15.2-*-win_amd64.whl'))) as archive:
        name=next(n for n in archive.namelist() if n.endswith('/gmsh-4.15.dll'))
        (target/'gmsh-4.15.dll').write_bytes(archive.read(name))
