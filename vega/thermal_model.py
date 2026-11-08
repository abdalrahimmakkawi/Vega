"""Distributed convection/conduction model with constant properties.

Gas reservoir temperature and film coefficients are explicit assumptions.
No radiation, boiling, axial conduction or circumferential spreading is modeled.
"""
from math import expm1, isfinite


def thermal_segment(inlet_k, gas_k, capacity_w_k, gas_area_m2, coolant_area_m2,
                    ligament_m, conductivity_w_m_k, gas_htc, coolant_htc):
    values=(inlet_k,gas_k,capacity_w_k,gas_area_m2,coolant_area_m2,
            ligament_m,conductivity_w_m_k,gas_htc,coolant_htc)
    if not all(isfinite(x) and x>0 for x in values):
        raise ValueError('Thermal segment requires finite positive SI inputs')
    rg=1/(gas_htc*gas_area_m2)
    rw=ligament_m/(conductivity_w_m_k*gas_area_m2)
    rc=1/(coolant_htc*coolant_area_m2)
    resistance=rg+rw+rc
    rise=(gas_k-inlet_k)*(-expm1(-1/(resistance*capacity_w_k)))
    outlet=inlet_k+rise
    heat=capacity_w_k*rise
    wall=[]
    for bulk in (inlet_k,outlet):
        local_heat=(gas_k-bulk)/resistance
        wall.append((gas_k-local_heat*rg,bulk+local_heat*rc,local_heat*rw))
    return {'bulk_inlet_k':inlet_k,'bulk_outlet_k':outlet,'heat_w':heat,
            'hot_wall_peak_k':max(w[0] for w in wall),
            'cold_wall_peak_k':max(w[1] for w in wall),
            'wall_gradient_peak_k':max(abs(w[2]) for w in wall),
            'gas_area_m2':gas_area_m2,'coolant_area_m2':coolant_area_m2,
            'resistance_k_w':{'gas':rg,'wall':rw,'coolant':rc},
            'energy_residual_w':heat-capacity_w_k*(outlet-inlet_k)}
