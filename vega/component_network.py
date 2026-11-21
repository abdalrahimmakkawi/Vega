"""Requirements connectivity, independent of display meshes and test plumbing."""
import hashlib
import json
import math


def component_model(design):
    """Provisional ambient-air topology; dimensions are never inferred from envelopes."""
    inventory = {p['id']: p for p in design['components']}
    components = []
    ports = []
    connections = []
    passages = []
    circuits = []
    used = set()

    def component(identity, geometry, role):
        if identity in used:
            return
        used.add(identity)
        components.append(dict(id=identity, geometry_ids=geometry, role=role,
            missing_geometry=[g for g in geometry if g not in inventory],
            requires_performance_map=identity in ('air-compressor', 'lp-compressor', 'hp-compressor', 'bypass-fan'),
            dimensions_mm=None, pressure_loss_model=None, thermal_model=None,
            mechanical_interface=None, performance_map=None))

    def port(owner, circuit, direction):
        identity = owner + '.' + circuit + '.' + direction
        ports.append(dict(id=identity, component=owner, circuit=circuit,
            direction=direction, fluid='air', required=True, diameter_mm=None,
            position_mm=None, outward_normal=None, interface=None))
        return identity

    def circuit(identity, members, reason):
        source, sink = identity + '-source', identity + '-sink'
        component(source, [], 'boundary'); component(sink, [], 'boundary')
        start = port(source, identity, 'out')
        previous = start
        for owner, geometry in members:
            component(owner, geometry, 'flow component')
            inlet = port(owner, identity, 'in'); outlet = port(owner, identity, 'out')
            connections.append(dict(source=previous, target=inlet, reason=reason))
            passages.append(dict(source=inlet, target=outlet, evidence='required; not geometrically verified'))
            previous = outlet
        end = port(sink, identity, 'in')
        connections.append(dict(source=previous, target=end, reason=reason))
        circuits.append(dict(id=identity, fluid='air', source=start, sink=end,
            boundary_conditions=None, requirement=reason))

    compressors = [('lp-compressor', ['lp-compressor']), ('intercooler', ['intercooler']),
                   ('hp-compressor', ['hp-compressor'])] if 'lp-compressor' in inventory else [('air-compressor', ['air-compressor'])]
    inlet = [('main-air-inlet', ['main-air-inlet'])] if 'main-air-inlet' in inventory else []
    circuit('main-air', inlet + [('precooler', ['precooler'])] + compressors + [('bell-chamber', ['bell-chamber'])],
            'Carry non-firing main air through exchanger air side, static compressor rows and chamber outlet.')
    circuit('bypass-air', [('bypass-fan', ['bypass-fan']), ('spill-duct', ['spill-duct']), ('bypass-nozzle', ['bypass-nozzle'])],
            'Provide a separate unheated bypass path; no shared test manifold or main-air cross connection.')
    circuit('exchanger-cooling', [('precooler', ['precooler']), ('intercooler', ['intercooler']), ('main-heat-exchanger', ['main-heat-exchanger'])],
            'Provisional independent ambient-air supply through exchanger secondary sides; no helium or cryogens.')
    circuit('jacket-cooling', [('core-jacket', ['half-a', 'half-b']), ('bell-jacket', ['bell-cooling-a', 'bell-cooling-b'])],
            'Independent ambient-air core-to-bell jacket flow, exhausting to ambient.')
    # Casing halves can be stored as bodies rather than recipe components.
    for c in components:
        c['missing_geometry'] = [g for g in c['missing_geometry'] if g not in design.get('body_ids', [])]
    assigned = {g for c in components for g in c['geometry_ids']}
    for identity, part in inventory.items():
        if identity in assigned:
            continue
        fixture = identity.startswith('cold-air-') or 'test-port' in identity
        components.append(dict(id=identity, geometry_ids=[identity], role='test fixture' if fixture else 'excluded representation',
            exclusion_reason='Shared inspection manifold is not an intended circuit.' if fixture else
                'Retained geometry; no fluid duty assigned in this non-firing baseline. Requires engineering review before activation.',
            dimensions_mm=None, pressure_loss_model=None, thermal_model=None, mechanical_interface=None, performance_map=None))
    if 'main-air-inlet' in inventory and design.get('inlet_revision'):
        inlet = design['inlet_revision']
        for p in ports:
            if p['component'] == 'main-air-inlet':
                upstream = p['direction'] == 'in'
                p.update(diameter_mm=2*inlet['mouth_radius_mm' if upstream else 'throat_radius_mm'],
                         position_mm=[0,0,-14 if upstream else 0], outward_normal=[0,0,-1 if upstream else 1],
                         interface='ambient opening' if upstream else 'flush casing seat')
    return dict(schema_version=1, scope='Provisional non-firing ambient-air requirements, not as-built connectivity',
        assumptions=['Separate main and bypass boundary supplies; inlet splitter and flow split are unresolved.',
                     'Cooling uses open ambient-air circuits; series exchanger order requires thermal review.',
                     'Static compressor rows have no pressure-rise or shaft-matching claim.'],
        components=components, ports=ports, connections=connections, passages=passages, circuits=circuits)


def check_connectivity(model):
    """Check directed port topology; report unknown engineering data separately."""
    errors, missing = [], []

    def index(key):
        result = {}
        for record in model[key]:
            identity = record['id']
            if not isinstance(identity, str) or not identity or identity in result:
                raise ValueError('Invalid or duplicate ' + key + ' ID: ' + str(identity))
            result[identity] = record
        return result

    components, ports, circuits = index('components'), index('ports'), index('circuits')
    graph = {p: set() for p in ports}
    counts = {p: 0 for p in ports}
    internal_counts = {p: 0 for p in ports}
    for identity, p in ports.items():
        if p['component'] not in components or p['circuit'] not in circuits or p['direction'] not in ('in', 'out'):
            errors.append('Invalid port ownership, circuit or direction: ' + identity)
        elif p['fluid'] != circuits[p['circuit']]['fluid']:
            errors.append('Circuit fluid mismatch: ' + identity)
        elif components[p['component']]['role'] not in ('boundary', 'flow component'):
            errors.append('Excluded component has active port: ' + identity)
        for key in ('diameter_mm', 'position_mm', 'outward_normal', 'interface'):
            value = p.get(key)
            if value is None:
                missing.append(identity + ':' + key)
            elif key == 'diameter_mm':
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                    errors.append('Invalid diameter: ' + identity)
            elif key in ('position_mm', 'outward_normal'):
                if not isinstance(value, list) or len(value) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
                    errors.append('Invalid ' + key + ': ' + identity)
                elif key == 'outward_normal' and not math.isclose(sum(v*v for v in value), 1., abs_tol=1e-6):
                    errors.append('Port normal must be unit length: ' + identity)
    for key, directions in [('connections', ('out', 'in')), ('passages', ('in', 'out'))]:
        seen = set()
        for edge in model[key]:
            a, b = edge['source'], edge['target']
            if a not in ports or b not in ports:
                errors.append('Dangling endpoint: ' + a + ' -> ' + b); continue
            pair = (a, b)
            if pair in seen:
                errors.append('Duplicate edge: ' + a + ' -> ' + b)
            seen.add(pair)
            p, q = ports[a], ports[b]
            valid = True
            if (p['direction'], q['direction']) != directions or p['fluid'] != q['fluid'] or p['circuit'] != q['circuit']:
                errors.append('Incompatible connection: ' + a + ' -> ' + b); valid = False
            if (p['component'] == q['component']) != (key == 'passages'):
                errors.append('Invalid component passage: ' + a + ' -> ' + b); valid = False
            if key == 'connections':
                if not edge.get('reason'):
                    errors.append('Connection lacks requirement: ' + a)
                for field in ('diameter_mm', 'interface'):
                    if p.get(field) is not None and q.get(field) is not None and p[field] != q[field]:
                        errors.append('Incompatible ' + field + ': ' + a + ' -> ' + b); valid = False
            counter = counts if key == 'connections' else internal_counts
            counter[a] += 1; counter[b] += 1
            if valid:
                graph[a].add(b)
    for identity, p in ports.items():
        if p['required'] and counts[identity] != 1:
            errors.append('Required port needs exactly one connection: ' + identity)
        owner = components.get(p['component'], {})
        expected = 0 if owner.get('role') == 'boundary' else 1
        if internal_counts[identity] != expected:
            errors.append('Invalid internal passage count: ' + identity)
    def reachable(start, edges):
        visited, pending = set(), [start]
        while pending:
            node = pending.pop()
            if node not in visited:
                visited.add(node); pending.extend(edges.get(node, ()))
        return visited
    reverse = {p: set() for p in ports}
    for a, targets in graph.items():
        for b in targets:
            reverse[b].add(a)
    for identity, circuit in circuits.items():
        source, sink = circuit['source'], circuit['sink']
        for endpoint, direction in [(source, 'out'), (sink, 'in')]:
            p = ports.get(endpoint, {})
            if p.get('circuit') != identity or p.get('direction') != direction or components.get(p.get('component'), {}).get('role') != 'boundary':
                errors.append('Invalid circuit boundary: ' + identity)
        required = {p for p, value in ports.items() if value['circuit'] == identity and value['required']}
        if not required or not required <= reachable(source, graph) & reachable(sink, reverse):
            errors.append('Disconnected circuit: ' + identity)
        if circuit.get('boundary_conditions') is None:
            missing.append(identity + ':boundary_conditions')
    for identity, c in components.items():
        if c['role'] not in ('boundary', 'flow component'):
            if not c.get('exclusion_reason'):
                errors.append('Unexplained excluded component: ' + identity)
            continue
        if c['role'] == 'flow component':
            if not any(p['component'] == identity for p in ports.values()):
                errors.append('Component has no ports: ' + identity)
            for field in ('dimensions_mm', 'pressure_loss_model', 'thermal_model', 'mechanical_interface'):
                if c.get(field) is None:
                    missing.append(identity + ':' + field)
            if c.get('requires_performance_map') and c.get('performance_map') is None:
                missing.append(identity + ':performance_map')
            missing.extend(identity + ':geometry:' + g for g in c.get('missing_geometry', []))
    return dict(topology_valid=not errors, errors=errors, missing_data=missing,
        ready_for_sizing=not errors and not missing, geometry_verified=False,
        scope='Port graph only. Does not prove openings, clearances, heat balance or machine matching.')


def assessment(report):
    design = dict(report['recipe'], body_ids=[b['component_id'] for b in report.get('bodies', [])])
    model = component_model(design)
    ports = {p['id']: p for p in model['ports']}
    components = {c['id']: c for c in model['components']}
    # Read outer envelope dimensions from the individual inspected solids.
    for c in components.values():
        if c['role'] != 'flow component':
            continue
        solids = [report.get('components', {}).get(g, {}) for g in c['geometry_ids']]
        if solids and all(s.get('size_mm') for s in solids):
            c['dimensions_mm'] = dict(zip(c['geometry_ids'], [s['size_mm'] for s in solids]))
            c['dimensions_source'] = 'Individual component STL bounding boxes in assembly axes'
    for owner, section in [('core-jacket','cooling'), ('bell-jacket','bell_cooling')]:
        routes = design.get(section, {}).get('ports', [])
        if len(routes) != 2:
            continue
        for direction, route in zip(('in','out'), routes):
            p = ports[f'{owner}.jacket-cooling.{direction}']
            a, b = route['points'][-2:]
            delta = [y-x for x,y in zip(a,b)]
            length = math.hypot(*delta)
            if length <= 0 or route['bore_radius_mm'] <= 0:
                raise ValueError('Degenerate cooling terminal: ' + p['id'])
            p.update(diameter_mm=2*route['bore_radius_mm'], position_mm=b,
                     outward_normal=[v/length for v in delta],
                     evidence=f'recipe.{section}.ports, nominal passage endpoint')
    inlet = design.get('inlet_revision', {})
    if inlet and 'main-air-inlet' in components:
        c = components['main-air-inlet']
        c['dimensions_mm'] = dict(mouth_bore=2*inlet['mouth_radius_mm'], throat_bore=2*inlet['throat_radius_mm'])
        c['mechanical_interface'] = inlet['interface']
    ref = design.get('synthesis', {}).get('reference', {})
    if ref and 'assumed_U_w_m2k' in ref:
        components['precooler']['thermal_model'] = dict(method='Constant sink temperature reference',
            assumed_U_w_m2k=ref['assumed_U_w_m2k'], sink_k=ref['assumed_coolant_temperature_k'],
            area_mm2=design['synthesis']['search']['selected']['surface_area_mm2'], source='recipe.synthesis')
        main = next(c for c in model['circuits'] if c['id']=='main-air')
        main['boundary_conditions'] = dict(inlet_mass_flow_kg_s=inlet['flow_g_s']/1000 if inlet else ref['mass_flow_kg_s'],
            inlet_temperature_k=ref['inlet_temperature_k'], outlet_static_pressure_pa=ref['pressure_pa'],
            evidence='Sizing assumptions using reference inflow and ambient discharge')
    # The saved revolved profiles define axial end planes. A rotor's profile
    # defines its hub, so it cannot establish the surrounding flow diameter.
    modules = design.get('architecture_modules', []) + design.get('concept_systems', {}).get('modules', [])
    for part in modules:
        owner = part['id']
        circuit = {'bell-chamber':'main-air', 'lp-compressor':'main-air',
                   'hp-compressor':'main-air', 'air-compressor':'main-air',
                   'bypass-fan':'bypass-air', 'spill-duct':'bypass-air',
                   'bypass-nozzle':'bypass-air'}.get(owner)
        if not circuit or owner not in components:
            continue
        if part['kind'] == 'rotor':
            components[owner]['requires_performance_map'] = False
            components[owner]['bench_motion'] = 'Fixed printed row, zero shaft work. Passive pressure-loss data required.'
        for direction, end, sign in [('in',0,-1), ('out',-1,1)]:
            port = ports.get(f'{owner}.{circuit}.{direction}')
            if port is None:
                continue
            z, radius = part['profile'][end]
            port.update(position_mm=[*part['center_mm'],z], outward_normal=[0,0,sign],
                        evidence='Nominal axial plane from saved module profile')
            if part['kind'] != 'rotor':
                port['diameter_mm'] = 2*(radius-part['wall'])
    # A boundary node represents the same cross-section as its adjacent terminal.
    for edge in model['connections']:
        a,b = ports[edge['source']], ports[edge['target']]
        for boundary, physical in ((a,b),(b,a)):
            if components[boundary['component']]['role'] != 'boundary':
                continue
            for field in ('diameter_mm','position_mm','interface','outward_normal'):
                value = physical[field]
                if value is not None:
                    boundary[field] = [-v for v in value] if field=='outward_normal' else value
                    boundary['evidence'] = 'Nominal boundary plane at '+physical['id']
    validation = check_connectivity(model)
    needed = dict(diameter_mm='Port bore drawing or gauge measurement',position_mm='Port centre in assembly coordinates',
        outward_normal='Port axis in assembly coordinates',interface='Mating interface drawing',
        dimensions_mm='Component dimensional drawing',pressure_loss_model='Cold-flow differential pressure versus flow',
        thermal_model='Thermal duty and heat-transfer characterization',mechanical_interface='Mount and mating interface drawing',
        performance_map='Machine map or approved passive bench representation',boundary_conditions='Supply and discharge conditions')
    return dict(model=model, validation=validation, concept_requirement=dict(net_thrust_target_n=11000,
        operating_point=dict(description='Sea-level static, standard atmosphere',altitude_m=0,
            mach=0, ambient_pressure_pa=101325, ambient_temperature_k=288.15),
        measured_net_thrust_n=None, verification_status='unverified',
        status='User-specified full-size design target'), outstanding_inputs=[
        dict(input_id=key, evidence_needed=needed.get(key.rsplit(':',1)[-1],'Component geometry evidence'))
        for key in validation['missing_data']],
        source_recipe_sha256=hashlib.sha256(json.dumps(report['recipe'], sort_keys=True, allow_nan=False).encode()).hexdigest())


def input_ledger(network):
    """Return the unresolved engineering inputs without inventing values."""
    inputs = list(network.get('outstanding_inputs', []))
    return dict(schema_version=1, status='incomplete' if inputs else 'complete',
        missing_input_count=len(inputs), inputs=inputs,
        source_recipe_sha256=network.get('source_recipe_sha256'))
