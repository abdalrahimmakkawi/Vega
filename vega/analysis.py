"""Executable, deliberately bounded CFD and structural FEA review cases.

CFD: axisymmetric, incompressible, irrotational potential flow, finite volumes.
FEA: Euler-Bernoulli beam elements for the centrebody's transverse tip load.
Neither is a full-engine, shock, thermal, rotating-machine or contact solution.
"""
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve


def centrebody_radius(z, travel=0):
    local=np.asarray(z)-travel
    return np.where((local>=-22)&(local<=64),
        np.interp(local,[-22,-6,6,16,20,64],[.8,4.8,8,8,2,2]),0.)


def potential_flow(inner, outer, *, step_mm=.5, flow_kg_s=.004, z_limits=(-24,24)):
    """Cell-centered FV of div(r grad(phi))=0; closed faces have zero flux."""
    z=np.arange(z_limits[0]+step_mm/2,z_limits[1],step_mm)
    r=np.arange(step_mm/2,float(np.max(outer(z)))+step_mm,step_mm)
    mask=(r[None,:]>inner(z)[:,None])&(r[None,:]<outer(z)[:,None])
    ids=np.full(mask.shape,-1,int); ids[mask]=np.arange(mask.sum())
    matrix=lil_matrix((mask.sum(),mask.sum())); rhs=np.zeros(mask.sum())
    # All lengths are converted to SI; the constant 2*pi cancels in the solve.
    h=step_mm*.001; rr=r*.001
    for i,j in np.argwhere(mask):
        row=ids[i,j]
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
            ni,nj=i+di,j+dj
            conductance=rr[j] if di else rr[j]+dj*h/2
            if ni<0 or ni>=len(z):
                matrix[row,row]+=2*conductance
                rhs[row]+=2*conductance*(ni>=len(z))
            elif 0<=nj<len(r) and mask[ni,nj]:
                matrix[row,row]+=conductance; matrix[row,ids[ni,nj]]-=conductance
    matrix=matrix.tocsr(); solution=spsolve(matrix,rhs)
    residual=float(np.linalg.norm(matrix@solution-rhs)/max(np.linalg.norm(rhs),1e-30))
    phi=np.full(mask.shape,np.nan); phi[mask]=solution
    qin=float(np.nansum(2*np.pi*rr*2*phi[0])); qout=float(np.nansum(2*np.pi*rr*2*(1-phi[-1])))
    scale=(flow_kg_s/1.2)/qin; phi*=scale
    uz=np.zeros_like(phi); ur=np.zeros_like(phi)
    # Average adjacent face velocities, including zero wall-normal flux.
    for i,j in np.argwhere(mask):
        left=2*phi[i,j]/h if i==0 else (phi[i,j]-phi[i-1,j])/h if mask[i-1,j] else 0
        right=2*(scale-phi[i,j])/h if i==len(z)-1 else (phi[i+1,j]-phi[i,j])/h if mask[i+1,j] else 0
        lower=(phi[i,j]-phi[i,j-1])/h if j>0 and mask[i,j-1] else 0
        upper=(phi[i,j+1]-phi[i,j])/h if j+1<len(r) and mask[i,j+1] else 0
        uz[i,j]=(left+right)/2; ur[i,j]=(lower+upper)/2
    speed=np.hypot(uz,ur)
    inlet_area=float(np.sum(2*np.pi*rr[mask[0]]*h)); inlet_speed=flow_kg_s/1.2/inlet_area
    pressure=.5*1.2*(inlet_speed**2-speed**2)
    sample=[]
    for i,j in np.argwhere(mask):
        sample.append([float(z[i]),float(r[j]),float(uz[i,j]),float(ur[i,j]),float(pressure[i,j])])
    return dict(method='Axisymmetric potential-flow CFD / finite volumes',cells=int(mask.sum()),
        grid_mm=step_mm,linear_relative_residual=residual,
        relative_mass_imbalance=abs(qout-qin)/abs(qin),peak_velocity_m_s=float(speed[mask].max()),
        inlet_velocity_m_s=inlet_speed,pressure_range_pa=[float(pressure[mask].min()),float(pressure[mask].max())],
        flow_kg_s=flow_kg_s,density_kg_m3=1.2,field_columns=['z_mm','r_mm','uz_m_s','ur_m_s','gauge_pressure_pa'],field=sample,
        boundary_conditions='Constant potential at inlet/outlet, scaled to reference mass flow; impermeable slip walls',
        scope='Intake meridional passage only. Incompressible, inviscid, irrotational; no shocks, viscosity, turbulence, heat transfer, tube bundle or compressor.',
        source='https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/bernoullis-equation-1/')


def beam_fea(nodes_mm, radius_mm, *, force_n=.1, young_pa=2e9):
    z=np.asarray(nodes_mm,float)*.001; radii=np.asarray(radius_mm,float)*.001
    n=len(z); k=lil_matrix((2*n,2*n)); load=np.zeros(2*n); load[0]=force_n
    elements=[]
    for i,length in enumerate(np.diff(z)):
        inertia=np.pi*radii[i]**4/4
        local=young_pa*inertia/length**3*np.array([
            [12,6*length,-12,6*length],[6*length,4*length**2,-6*length,2*length**2],
            [-12,-6*length,12,-6*length],[6*length,2*length**2,-6*length,4*length**2]])
        dofs=np.arange(2*i,2*i+4)
        for a in range(4):
            for b in range(4): k[dofs[a],dofs[b]]+=local[a,b]
        elements.append((dofs,local,inertia))
    k=k.tocsr(); free=np.arange(2*n-2); u=np.zeros(2*n)
    u[free]=spsolve(k[free][:,free],load[free])
    reaction=k@u-load
    stress=[]
    for i,(dofs,local,inertia) in enumerate(elements):
        actions=local@u[dofs]
        stress.append(float(max(abs(actions[1]),abs(actions[3]))*radii[i]/inertia))
    return dict(method='Euler-Bernoulli bending FEA / cubic Hermite beam elements',elements=n-1,
        assumed_young_modulus_pa=young_pa,tip_force_n=force_n,
        tip_displacement_mm=float(u[0]*1000),maximum_bending_stress_pa=max(stress),
        relative_equilibrium_residual=float(np.linalg.norm(reaction[free])/max(abs(force_n),1e-30)),
        support_reaction_n=float(reaction[-2]),support_moment_nm=float(reaction[-1]),
        nodes_z_mm=(z*1000).tolist(),displacement_mm=(u[::2]*1000).tolist(),element_bending_stress_pa=stress,
        boundary_conditions='0.1 N lateral tip load; displacement and rotation clamped at guide entry z=48 mm',
        scope='Centrebody beam idealization. Assumed isotropic E=2 GPa; excludes guide contact, print anisotropy, local notch stress, pressure, vibration and thermal stress. No strength acceptance is claimed.',
        source='https://teachbooks.tudelft.nl/computational-modelling/structural_linear/euler_bernouilli.html')


def analyze(design):
    travel=design['intake']['centrebody_mm']
    inner=lambda z:centrebody_radius(z,travel)
    rows=design['outer']; outer=lambda z:np.interp(z,[p['z_mm'] for p in rows],[p['radii_mm'][0] for p in rows])
    flow=design['synthesis']['reference']['mass_flow_kg_s']
    coarse=potential_flow(inner,outer,step_mm=1,flow_kg_s=flow)
    fine=potential_flow(inner,outer,step_mm=.5,flow_kg_s=flow)
    fine['grid_comparison']=dict(coarse_mm=1,fine_mm=.5,
        peak_velocity_change_percent=100*abs(fine['peak_velocity_m_s']-coarse['peak_velocity_m_s'])/fine['peak_velocity_m_s'],
        status='Two-grid sensitivity only; grid independence is not established')
    def structural(count):
        # Include every profile corner so section changes do not straddle elements.
        corners=np.r_[np.array([-22,-6,6,16,20])+travel,48.]
        spacing=(48-corners[0])/count
        nodes=np.unique(np.concatenate([np.linspace(a,b,max(2,int(np.ceil((b-a)/spacing))+1))
            for a,b in zip(corners[:-1],corners[1:])]))
        return beam_fea(nodes,inner((nodes[:-1]+nodes[1:])/2))
    first=structural(40); second=structural(80)
    second['mesh_comparison']=dict(coarse_elements=first['elements'],fine_elements=second['elements'],
        tip_displacement_change_percent=100*abs(second['tip_displacement_mm']-first['tip_displacement_mm'])/abs(second['tip_displacement_mm']))
    if fine['linear_relative_residual']>1e-8 or fine['relative_mass_imbalance']>1e-8 or second['relative_equilibrium_residual']>1e-5:
        raise ValueError('CFD/FEA numerical residual gate failed')
    return dict(status='Solved reduced models; physical validation pending',geometry_recipe_sha256=design['recipe_sha256'],
        centrebody_mm=travel,cfd=fine,fea=second,full_engine_cfd=False,full_assembly_fea=False,
        shock_solution=False,helium_or_hydrogen_performance=False)
