"""MAC-APPLY glue — mount on beta-os sidecar ONLY (e.g. :8790), never prod :8787.

Example (inside beta request handler):

    from owner_trading_ro import load_trading_ro
    from owner_fitness_ro import load_fitness_ro

    if path == "/api/owner/trading-ro":
        return json_response(load_trading_ro())
    if path == "/api/owner/fitness-ro":
        return json_response(load_fitness_ro())

Copy owner_trading_ro.py + owner_fitness_ro.py next to beta serve modules.
"""
