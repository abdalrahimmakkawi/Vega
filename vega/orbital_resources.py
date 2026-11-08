"""Conditional circular-Earth-orbit power, eclipse energy and radiator sizing."""
import math


def size_orbital_resources(brief):
    values=[brief.orbit_altitude_m,brief.orbital_electrical_load_w,brief.power_margin_fraction,
        brief.solar_array_efficiency,brief.solar_eol_factor,brief.battery_depth_of_discharge,
        brief.battery_specific_energy_wh_kg,brief.radiator_emissivity,
        brief.radiator_temperature_k,brief.radiator_sink_temperature_k]
    if not all(math.isfinite(value) for value in values) or min(values)<0:
        raise ValueError('Orbital resource boundaries must be finite and nonnegative')
    if not all(0<v<=1 for v in (brief.solar_array_efficiency,brief.solar_eol_factor,brief.battery_depth_of_discharge,brief.radiator_emissivity)) or brief.battery_specific_energy_wh_kg<=0:
        raise ValueError('Invalid efficiency, emissivity or battery performance')
    radius=6371000+brief.orbit_altitude_m;mu=3.986004418e14
    period=2*math.pi*math.sqrt(radius**3/mu)
    # Central eclipse, cylindrical Earth shadow and zero solar beta angle.
    eclipse=period*math.asin(6371000/radius)/math.pi
    sunlight=period-eclipse
    load=brief.orbital_electrical_load_w*(1+brief.power_margin_fraction)
    charge_efficiency=.9;discharge_efficiency=.95;solar_flux=1361.
    eclipse_load_wh=load*eclipse/3600
    discharge_wh=eclipse_load_wh/discharge_efficiency
    battery_wh=discharge_wh/brief.battery_depth_of_discharge
    charge_wh=discharge_wh/charge_efficiency
    array_power=load+charge_wh*3600/sunlight
    area=array_power/(solar_flux*brief.solar_array_efficiency*brief.solar_eol_factor)
    solar_mass=area*5.0;battery_mass=battery_wh/brief.battery_specific_energy_wh_kg
    sigma=5.670374419e-8
    flux=brief.radiator_emissivity*sigma*(brief.radiator_temperature_k**4-brief.radiator_sink_temperature_k**4)
    if flux<=0:raise ValueError('Radiator must be hotter than the assumed effective sink')
    # Conservative electrical heat budget: all design electrical load plus
    # mean charge/discharge losses becomes heat at one isothermal node.
    battery_loss_wh=charge_wh-eclipse_load_wh
    heat=load+battery_loss_wh*3600/period
    radiator_area=heat/flux;radiator_mass=radiator_area*6.0
    solar_energy_wh=array_power*sunlight/3600
    load_energy_wh=load*period/3600
    residual=solar_energy_wh-load_energy_wh-battery_loss_wh
    radiator_residual=radiator_area*flux-heat
    return {'status':'conditional_orbital_resource_sizing',
        'orbit':{'period_s':period,'eclipse_s':eclipse,'sunlight_s':sunlight,'eclipse_fraction':eclipse/period},
        'power':{'design_load_w':load,'assumed_electrical_load_w':brief.orbital_electrical_load_w,
            'array_sunlight_power_w':array_power,'array_area_m2':area,'battery_nominal_energy_wh':battery_wh,
            'eclipse_load_energy_wh':eclipse_load_wh,'battery_loss_wh_per_orbit':battery_loss_wh,
            'orbital_energy_residual_wh':residual},
        'thermal':{'electrical_heat_rejection_w':heat,'radiator_area_m2':radiator_area,
            'net_radiative_flux_w_m2':flux,'radiator_temperature_k':brief.radiator_temperature_k,
            'effective_sink_temperature_k':brief.radiator_sink_temperature_k,'heat_balance_residual_w':radiator_residual},
        'component_masses_kg':{'solar_arrays':solar_mass,'eclipse_battery':battery_mass,'orbital_radiator':radiator_mass},
        'checks':{'orbital_energy_balance':abs(residual)<=max(1e-8,load_energy_wh*1e-10),
            'radiator_heat_balance':abs(radiator_residual)<=max(1e-8,heat*1e-10),
            'positive_sunlight_duration':sunlight>0},
        'assumptions':{'solar_flux_w_m2':solar_flux,'array_areal_mass_kg_m2':5.0,'radiator_areal_mass_kg_m2':6.0,
            'battery_charge_efficiency':charge_efficiency,'battery_discharge_efficiency':discharge_efficiency,
            'solar_array_efficiency':brief.solar_array_efficiency,'solar_eol_factor':brief.solar_eol_factor,
            'battery_depth_of_discharge':brief.battery_depth_of_discharge,
            'battery_specific_energy_wh_kg':brief.battery_specific_energy_wh_kg,
            'radiator_emissivity':brief.radiator_emissivity,'power_margin_fraction':brief.power_margin_fraction},
        'scope':'Circular Earth orbit, zero-beta central eclipse, normal solar incidence and constant load. No orbit lifetime, attitude solution, transient temperatures, surface view factors, solar/albedo heating, array pointing/deployment, peak loads, battery cycling qualification, power distribution hardware, atmospheric heating or reentry model. Radiator uses one isothermal emitting face and a user-assumed effective sink. Areal masses and battery performance are assumptions, not selected hardware.',
        'sources':['https://www.nasa.gov/smallsat-institute/sst-soa/power-subsystems/',
            'https://www.nasa.gov/wp-content/uploads/2021/10/7.soa_thermal_2021_0.pdf']}
