"""Run-bound mesh/solver study; every output is tied to source geometry hashes."""
from pathlib import Path
import hashlib
import json
import zipfile
import numpy as np
from . import VERSION
from .hybrid import build_hybrid, write_msh, inspection_scene
from .airpath import build_airpath
from .solvers import run_cfd, probe, linux_run
from .fea import run_frame, frame_decks


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_study(run,root,progress=lambda message:None):
    assembly=run['candidates'][0].get('assembly',{})
    if assembly.get('status')!='concept_assembly':
        return {'status':'not_applicable','reason':'Hybrid passage study requires the connected duct assembly.'}
    if run['requirements'].get('inlet_section','elliptical')!='elliptical':
        return {'status':'unsupported_section','reason':'CAD walls support rectangles; hybrid flow sweep currently requires elliptical/lobed sections.'}
    folder=Path(root)/'data/analysis'/run['id'];folder.mkdir(parents=True,exist_ok=True)
    stations=assembly['sections'][-1]
    input_record={'backend':VERSION,'run_id':run['id'],'assembly_recipe_sha256':assembly['recipe_sha256'],
        'core_stl_sha256':run.get('artifact',{}).get('stl_sha256'),'frame_members':assembly['frame_members'],
        'domain':'common_nozzle_unobstructed_cold_flow','stations':stations,
        'surface_edge_mm':run['requirements'].get('mesh_surface_edge_mm',12),
        'run_solvers':bool(run['requirements'].get('mesh_run_solvers',1)),
        'duct_stages':assembly['sections']}
    (folder/'inputs.json').write_text(json.dumps(input_record,indent=2))
    # Independent volume controls avoid millions of cells when the display
    # chord tolerance changes. The chosen target and all cell counts are shown.
    span=stations[-1]['z_mm']-stations[0]['z_mm']
    edge=max(span/96,run['requirements'].get('mesh_surface_edge_mm',12))
    progress('Building conforming Gmsh prism / hex flow volume…')
    coarse=build_hybrid(stations,edge,sectors=48,layers=6)
    write_msh(coarse,folder/'coarse.msh')
    result={'schema_version':1,'version':VERSION,'status':'mesh_only','input_sha256':digest(folder/'inputs.json'),
        'source':{k:input_record[k] for k in ('run_id','assembly_recipe_sha256','core_stl_sha256','domain')},
        'coarse_mesh':coarse.summary,'runtime':probe(),'adaptation':None,
        'scope':'Common-nozzle cold-flow domain and optimized frame; no combustion, coupled hot-wall stress or whole-spacecraft certification.'}
    result['nozzle_verification_gate']={
        'status':'not_verified',
        'required_domain':'isolated rocket core nozzle',
        'required_meshes':3,'minimum_refinement_ratio':1.3,
        'required_outputs':['thrust','mass_flow','exit_pressure','wall_heat_flux_profile'],
        'reason':'This study models the common nozzle using incompressible cold flow; it does not provide the required rocket-nozzle compressible, thermal, three-grid comparison.',
        'coupled_analysis_authorized':False}
    selected=coarse
    frame_decks(assembly,folder/'fea')
    if input_record['run_solvers']:
        progress('Solving coarse OpenFOAM flow and measuring velocity gradients…')
        try:
            first=run_cfd(coarse,folder/'coarse',stations,iterations=500)
            result['coarse_cfd']=first
            result['adaptation_source']={'time':first['time'],
                'indicator':first['adaptation_indicator'],'converged':first['converged']}
            progress('Adapting volume cells to the solved velocity gradient…')
            fine=build_hybrid(stations,edge,sectors=48,layers=6,indicators=first['adaptation_indicator'])
            write_msh(fine,folder/'adaptive.msh')
            selected=fine;result['adaptive_mesh']=fine.summary
            progress('Solving the adaptive OpenFOAM mesh and comparing pressure drop…')
            second=run_cfd(fine,folder/'adaptive',stations,iterations=700)
            result['adaptive_cfd']=second
            change=abs(second['pressure_drop_pa']-first['pressure_drop_pa'])/max(abs(second['pressure_drop_pa']),1e-12)
            result['adaptation']={'passes':2,'indicator':first['indicator_kind'],
                'coarse_cells':coarse.summary['cells'],'adaptive_cells':fine.summary['cells'],
                'relative_pressure_drop_change':change,'convergence_tolerance':.05,
                'converged':bool(first['converged'] and second['converged'] and change<.05),
                'scope':'One solution-driven axial refinement pass. Radial/turbulence/model independence remains unproven.'}
            result['status']='computed' if result['adaptation']['converged'] else 'computed_not_converged'
            # Fluent's own legacy mesh format, generated from the checked polyMesh.
            try:
                linux_run(['foamMeshToFluent'],folder/'adaptive','fluent-export.log',120)
                result['ansys_fluent_export']='written'
            except RuntimeError as error:result['ansys_fluent_export']={'status':'failed','error':str(error)}
        except (RuntimeError,ValueError,OSError) as error:
            result['status']='solver_failed';result['cfd_error']=str(error)
        progress('Checking the selected topology-optimized frame with CalculiX…')
        try:result['fea']=run_frame(assembly,folder/'fea')
        except (RuntimeError,ValueError,OSError) as error:
            result['fea']={'status':'failed','error':str(error)};result['status']='solver_failed'
    else:
        result['fea']={'status':'deck_written_not_solved'}
    write_msh(selected,folder/'selected.msh')
    (folder/'scene.json').write_text(json.dumps(inspection_scene(selected),separators=(',',':')))
    np.savez_compressed(folder/'volume.npz',nodes_mm=selected.nodes,prisms=selected.cells[6],
                        hexahedra=selected.cells[5],axial_levels_mm=selected.axial_levels)
    result['selected_mesh']=selected.summary
    try:
        progress('Building and checking the five-stage airpath volume…')
        airpath, air_stations=build_airpath(assembly,input_record['surface_edge_mm'])
        write_msh(airpath,folder/'airpath.msh')
        (folder/'airpath-scene.json').write_text(json.dumps(inspection_scene(airpath),separators=(',',':')))
        np.savez_compressed(folder/'airpath-volume.npz',nodes_mm=airpath.nodes,
            prisms=airpath.cells[6],hexahedra=airpath.cells[5],axial_levels_mm=airpath.axial_levels)
        result['airpath_mesh']=airpath.summary
        if input_record['run_solvers']:
            progress('Solving cold flow through all five connected duct stages…')
            result['airpath_cfd']=run_cfd(airpath,folder/'airpath',air_stations,iterations=600)
    except (RuntimeError,ValueError,OSError) as error:
        result['airpath_error']=str(error)
    names=['selected.msh','volume.npz','scene.json']
    names.extend(name for name in ('airpath.msh','airpath-volume.npz','airpath-scene.json') if (folder/name).is_file())
    result['files']={name:digest(folder/name) for name in names}
    result['ansys_status']=result['runtime']['ansys']['status']
    refresh_archive(folder,result)
    return result


def refresh_archive(folder,result):
    folder=Path(folder)
    result['files'].pop('engineering-mesh.zip',None)
    (folder/'report.json').write_text(json.dumps(result,indent=2))
    # The archive contains inputs, mesh, solver dictionaries, solution fields,
    # logs, FEA decks/results and report. Exclude itself and helper launch scripts.
    with zipfile.ZipFile(folder/'engineering-mesh.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob('*')):
            if path.is_file() and path.name!='engineering-mesh.zip' and not path.name.startswith('.run-'):
                archive.write(path,path.relative_to(folder).as_posix())
    result['files']['engineering-mesh.zip']=digest(folder/'engineering-mesh.zip')


def artifact_path(run,root,name):
    allowed={'selected.msh','volume.npz','scene.json','airpath.msh','airpath-volume.npz',
        'airpath-scene.json','engineering-mesh.zip'}
    report=run.get('mesh_study',{})
    if name not in allowed or name not in report.get('files',{}):raise ValueError('Mesh artifact unavailable')
    path=Path(root)/'data/analysis'/run['id']/name
    if not path.is_file() or digest(path)!=report['files'][name]:raise ValueError('Mesh artifact identity mismatch')
    if report.get('source',{}).get('assembly_recipe_sha256')!=run['candidates'][0]['assembly']['recipe_sha256']:
        raise ValueError('Mesh study belongs to a different assembly')
    return path
