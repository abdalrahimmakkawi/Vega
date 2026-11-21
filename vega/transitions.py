"""Simulation-only mode-request guards. Does not control any hardware."""

REQUIRED = {
    ('airbreathing','rocket'): ('engine_cycle_valid','oxidizer_feed_ready','intake_isolated','chamber_stable'),
    ('rocket','airbreathing'): ('engine_cycle_valid','inlet_flow_stable','precooler_ready','compressor_ready','chamber_stable'),
}


def assess_transition(current, requested, evidence):
    if (current,requested) not in REQUIRED:
        raise ValueError('Unsupported mode transition')
    missing=[name for name in REQUIRED[(current,requested)] if evidence.get(name) is not True]
    return dict(current=current,requested=requested,
        status='inhibited' if missing else 'simulation_guard_satisfied',missing=missing,
        flight_transition_verified=False,
        scope='Boolean simulation guards only. No transient dynamics, flight envelope or hardware command.')
