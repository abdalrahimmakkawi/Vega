"""Local solver adapters with bounded execution, explicit units and saved logs."""
from pathlib import Path
import json
import os
import re
import shlex
import subprocess
import sys
import numpy as np
from . import ROOT
from .hybrid import write_msh


def linux_path(path):
    p=Path(path).resolve()
    if os.name!='nt': return str(p)
    return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]


def linux_run(arguments,folder,log_name,timeout=300):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    # Bound the Linux process too: terminating only wsl.exe can leave work alive.
    command='source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1\ncd '+shlex.quote(linux_path(folder))+' || exit 1\nexec timeout --signal=TERM --kill-after=5s '+str(max(1,timeout-10))+'s '+shlex.join(arguments)+'\n'
    script=folder/('.run-'+Path(log_name).stem+'.sh')
    script.write_text(command,encoding='utf-8',newline='\n')
    argv=['wsl','-d','Ubuntu-22.04','--exec','bash',linux_path(script)] if os.name=='nt' else ['bash',str(script)]
    try:
        result=subprocess.run(argv,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired as error:
        (folder/log_name).write_bytes((error.stdout or b'')+(error.stderr or b''))
        raise RuntimeError(f'{arguments[0]} exceeded {timeout} seconds; inspect {log_name}') from error
    text=(result.stdout+result.stderr).decode('utf-8',errors='replace').replace('\x00','')
    (folder/log_name).write_text(text,encoding='utf-8')
    if result.returncode or 'FOAM FATAL' in text:
        raise RuntimeError(f'{arguments[0]} failed; inspect {folder/log_name}: '+text[-1200:])
    return text


def probe():
    result={'gmsh':{},'openfoam':{},'calculix':{},'ansys':{}}
    import gmsh
    result['gmsh']={'installed':True,'version':gmsh.__version__}
    try:
        text=linux_run(['dpkg-query','-W','openfoam','calculix-ccx'],ROOT/'tmp/solver-probe','versions.log',45)
        for key,package in (('openfoam','openfoam'),('calculix','calculix-ccx')):
            match=re.search(r'^'+package+r'\s+([^\r\n]+)',text,re.M)
            result[key]={'installed':bool(match),'version':match[1] if match else None,'host':'Ubuntu-22.04 / WSL'}
    except (OSError,RuntimeError) as e:
        result['openfoam']=result['calculix']={'installed':False,'error':str(e)}
    exe=os.environ.get('VEGA_MAPDL_EXECUTABLE')
    result['ansys']={'clients_installed':(ROOT/'.tools/ansys/ansys/mapdl/core').is_dir() and (ROOT/'.tools/ansys/ansys/fluent/core').is_dir(),
        'solver_configured':bool(exe and Path(exe).is_file()),'license_verified':False,
        'status':'Configured, not yet license-tested' if exe and Path(exe).is_file() else 'Solver installation and license required; Python clients are not solver executables.'}
    return result


def _foam_header(kind,name):
    return f'FoamFile\n{{ version 2.0; format ascii; class {kind}; object {name}; }}\n'


def prepare_cfd(mesh,folder,velocity=.1,viscosity=1e-3,iterations=400):
    """Low-Re incompressible cold-flow verification case, never a rocket hot-flow claim."""
    folder=Path(folder)
    if not 0<velocity<10 or not 0<viscosity<1 or not 10<=iterations<=3000: raise ValueError('Invalid CFD verification inputs')
    for name in ('0','constant','system'): (folder/name).mkdir(parents=True,exist_ok=True)
    write_msh(mesh,folder/'flow.msh')
    def write(name,text,kind='dictionary'):
        (folder/name).write_text(_foam_header(kind,Path(name).name)+text,encoding='ascii')
    write('system/controlDict',f'''application simpleFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime {iterations}; deltaT 1;
writeControl timeStep; writeInterval {iterations}; purgeWrite 0; writeFormat ascii;
writePrecision 12; writeCompression off; timeFormat general; timePrecision 8; runTimeModifiable false;
functions
{{
 inletFlow {{ type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 20;
 regionType patch; name inlet; operation sum; fields (phi); writeFields false; }}
 outletFlow {{ type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 20;
 regionType patch; name outlet; operation sum; fields (phi); writeFields false; }}
 inletPressure {{ type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 20;
 regionType patch; name inlet; operation areaAverage; fields (p); writeFields false; }}
 outletPressure {{ type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 20;
 regionType patch; name outlet; operation areaAverage; fields (p); writeFields false; }}
}}
''')
    write('system/fvSchemes','''ddtSchemes { default steadyState; }
gradSchemes { default cellLimited Gauss linear 1; }
divSchemes { default none; div(phi,U) bounded Gauss linearUpwind grad(U); div((nuEff*dev2(T(grad(U))))) Gauss linear; }
laplacianSchemes { default Gauss linear limited 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited 0.5; }
wallDist { method meshWave; }
''')
    write('system/fvSolution','''solvers {
p { solver GAMG; tolerance 1e-9; relTol 0.02; smoother GaussSeidel; }
U { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-10; relTol 0.05; }
}
SIMPLE { nNonOrthogonalCorrectors 2; consistent yes; residualControl { p 1e-6; U 1e-7; } }
relaxationFactors { fields { p 0.3; } equations { U 0.7; } }
''')
    write('constant/transportProperties',f'transportModel Newtonian; nu [0 2 -1 0 0 0 0] {viscosity};\n')
    write('constant/turbulenceProperties','simulationType laminar;\n')
    write('0/U',f'''dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 {velocity});
boundaryField {{ inlet {{ type fixedValue; value uniform (0 0 {velocity}); }}
outlet {{ type zeroGradient; }} wall {{ type noSlip; }} }}
''','volVectorField')
    write('0/p','''dimensions [0 2 -2 0 0 0 0]; internalField uniform 0;
boundaryField { inlet { type zeroGradient; } outlet { type fixedValue; value uniform 0; } wall { type zeroGradient; } }
''','volScalarField')
    (folder/'inputs.json').write_text(json.dumps({'velocity_m_s':velocity,'kinematic_viscosity_m2_s':viscosity,
        'density_kg_m3':1.225,'solver':'simpleFoam','model':'steady incompressible laminar cold-flow verification','mesh':mesh.summary},indent=2))


def _field(path,vector=False):
    text=Path(path).read_text()
    match=re.search(r'internalField\s+nonuniform\s+List<\w+>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
    if not match: raise ValueError('Expected a nonuniform ASCII OpenFOAM field: '+str(path))
    values=np.fromstring(match[2].replace('(',' ').replace(')',' '),sep=' ')
    return values.reshape(int(match[1]),3 if vector else 1)


def run_cfd(mesh,folder,stations,velocity=.1,viscosity=1e-3,iterations=400):
    folder=Path(folder);prepare_cfd(mesh,folder,velocity,viscosity,iterations)
    linux_run(['gmshToFoam','flow.msh'],folder,'conversion.log',120)
    check=linux_run(['checkMesh','-allTopology','-allGeometry'],folder,'checkMesh.log',120)
    if 'Mesh OK.' not in check: raise RuntimeError('OpenFOAM rejected volume quality; inspect checkMesh.log')
    log=linux_run(['simpleFoam'],folder,'simpleFoam.log',900)
    summary=summarize_cfd(folder,stations,log,iterations)
    if not summary['converged']:
        summary=resume_cfd(folder,stations,end_time=min(2000,iterations+900))
    return summary


def resume_cfd(folder,stations,end_time=1500):
    """Continue a checked case from its saved fields without altering its mesh."""
    folder=Path(folder)
    if not (folder/'result.json').is_file() or 'Mesh OK.' not in (folder/'checkMesh.log').read_text():
        raise ValueError('Resume requires a completed, checked case and result record')
    previous=json.loads((folder/'result.json').read_text())
    if previous['converged']:return previous
    if not previous['time']<end_time<=3000:raise ValueError('Resume limit must exceed the saved time and be <=3000')
    control=folder/'system/controlDict';text=control.read_text()
    text=re.sub(r'startFrom\s+\w+;', 'startFrom latestTime;',text)
    text=re.sub(r'endTime\s+[\d.eE+-]+;',f'endTime {end_time};',text)
    text=re.sub(r'writeInterval\s+[\d.eE+-]+;', 'writeInterval 100;',text,count=1)
    control.write_text(text,encoding='ascii')
    log=linux_run(['simpleFoam'],folder,f'simpleFoam-resume-{end_time}.log',900)
    summary=summarize_cfd(folder,stations,log,end_time)
    summary['resumed_from']=previous['time']
    (folder/'result.json').write_text(json.dumps(summary,indent=2));return summary


def summarize_cfd(folder,stations,log,iterations):
    folder=Path(folder)
    times=sorted((p for p in folder.iterdir() if p.is_dir() and re.fullmatch(r'\d+(?:\.\d+)?',p.name) and float(p.name)>0),key=lambda p:float(p.name))
    if not times: raise RuntimeError('OpenFOAM produced no solution time')
    latest=times[-1]
    linux_run(['postProcess','-func','writeCellCentres','-latestTime'],folder,'centres.log',120)
    xyz=_field(latest/'C',True);u=_field(latest/'U',True)
    if not np.isfinite(u).all(): raise RuntimeError('Nonfinite CFD velocity')
    def last_value(name):
        files=sorted((folder/'postProcessing'/name).glob('*/surfaceFieldValue.dat'),key=lambda p:float(p.parent.name))
        if not files: raise RuntimeError('Missing CFD integral: '+name)
        rows=[line for line in files[-1].read_text().splitlines() if line.strip() and not line.startswith('#')]
        return float(rows[-1].split()[-1])
    qin,qout=last_value('inletFlow'),last_value('outletFlow')
    pin,pout=last_value('inletPressure'),last_value('outletPressure')
    balance=abs(qin+qout)/max(abs(qin),1e-30)
    levels=np.array([s['z_mm'] for s in stations])/1000
    speed=np.linalg.norm(u,axis=1)
    interval=np.clip(np.searchsorted(levels,xyz[:,2],side='right')-1,0,len(levels)-2)
    mean=np.array([float(speed[interval==i].mean()) if np.any(interval==i) else 0. for i in range(len(levels)-1)])
    # A recovered axial velocity-gradient indicator, not a certified error bound.
    gradient=abs(np.gradient(mean,(levels[1:]+levels[:-1])/2)) if len(mean)>1 else np.ones(1)
    indicator=gradient/max(float(gradient.max()),1e-30)
    residual={}
    for field,initial in re.findall(r'Solving for (\w+), Initial residual = ([\deE+.-]+)',log):residual[field]=float(initial)
    converged=all(residual.get(k,1)>-1 and residual.get(k,1)<1e-6 for k in ('p','Ux','Uy','Uz')) and balance<1e-4
    summary={'solver':'OpenFOAM simpleFoam','time':float(latest.name),'iterations_limit':iterations,
        'checkMesh':'passed','residuals':residual,'converged':converged,
        'inlet_flow_m3_s':qin,'outlet_flow_m3_s':qout,'relative_mass_imbalance':balance,
        'pressure_drop_pa':(pin-pout)*1.225,'maximum_velocity_m_s':float(speed.max()),
        'adaptation_indicator':indicator.tolist(),'indicator_kind':'recovered interval mean velocity gradient',
        'scope':'Low-Re, cold incompressible duct verification; not hot rocket/airbreathing performance.'}
    (folder/'result.json').write_text(json.dumps(summary,indent=2));return summary


if __name__=='__main__':
    if '--probe' in sys.argv:print(json.dumps(probe(),indent=2))
