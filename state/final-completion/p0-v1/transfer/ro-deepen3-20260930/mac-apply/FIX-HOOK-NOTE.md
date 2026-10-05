# deepen3 hook fix (2026-09-30)

ONE_SHOT initially left only import + placeholder (trading-ro regex miss).
Applied: `from core.hkegcav_ro_routes import try_hkegcav_ro` + dispatch after fitness-ro using `_send_json`.
Probes: 10/10 → 200 V1_RO_OK on :8788. Prod :8787 untouched.
