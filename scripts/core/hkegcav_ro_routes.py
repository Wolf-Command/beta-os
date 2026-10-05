"""Beta-only RO route helper for Habitat/Kuta/EventBus/Gatekeeper/Content/Ads/Resolve/Voice.
Never mount on prod :8787.
"""
def try_hkegcav_ro(path, json_response):
    p = path.rstrip("/")
    load_habitat_investment_ro = load_kuta_rates_ro = load_gatekeeper_ro = None
    load_event_bus_ro = load_content_ro = load_ads_studio_ro = None
    load_resolve_studio_ro = load_voice_ro = load_amg_voice_ro = None
    load_bzg_voice_ro = load_ggv_voice_ro = None
    try:
        from core.owner_habitat_investment_ro import load_habitat_investment_ro
        from core.ops_kuta_rates_ro import load_kuta_rates_ro
        from core.owner_gatekeeper_ro import load_gatekeeper_ro
        from core.ops_event_bus_ro import load_event_bus_ro
        from core.seats_content_ro import load_content_ro
        from core.seats_ads_studio_ro import load_ads_studio_ro
        from core.seats_resolve_studio_ro import load_resolve_studio_ro
        from core.voice_boards_ro import load_voice_ro, load_amg_voice_ro, load_bzg_voice_ro, load_ggv_voice_ro
    except Exception:
        try:
            from owner_habitat_investment_ro import load_habitat_investment_ro
            from ops_kuta_rates_ro import load_kuta_rates_ro
            from owner_gatekeeper_ro import load_gatekeeper_ro
            from ops_event_bus_ro import load_event_bus_ro
            from seats_content_ro import load_content_ro
            from seats_ads_studio_ro import load_ads_studio_ro
            from seats_resolve_studio_ro import load_resolve_studio_ro
            from voice_boards_ro import load_voice_ro, load_amg_voice_ro, load_bzg_voice_ro, load_ggv_voice_ro
        except Exception:
            try:
                from scripts.core.owner_habitat_investment_ro import load_habitat_investment_ro
                from scripts.core.ops_kuta_rates_ro import load_kuta_rates_ro
                from scripts.core.owner_gatekeeper_ro import load_gatekeeper_ro
                from scripts.core.ops_event_bus_ro import load_event_bus_ro
                from scripts.core.seats_content_ro import load_content_ro
                from scripts.core.seats_ads_studio_ro import load_ads_studio_ro
                from scripts.core.seats_resolve_studio_ro import load_resolve_studio_ro
                from scripts.core.voice_boards_ro import load_voice_ro, load_amg_voice_ro, load_bzg_voice_ro, load_ggv_voice_ro
            except Exception:
                return None
    routes = {
        "/api/owner/habitat-investment-ro": load_habitat_investment_ro,
        "/api/ops/kuta-rates-ro": load_kuta_rates_ro,
        "/api/owner/gatekeeper-ro": load_gatekeeper_ro,
        "/api/ops/event-bus-ro": load_event_bus_ro,
        "/api/seats/content-ro": load_content_ro,
        "/api/seats/ads-studio-ro": load_ads_studio_ro,
        "/api/seats/resolve-studio-ro": load_resolve_studio_ro,
        "/api/voice/ro": load_voice_ro,
        "/api/voice/amg-ro": load_amg_voice_ro,
        "/api/voice/bzg-ro": load_bzg_voice_ro,
        "/api/voice/ggv-ro": load_ggv_voice_ro,
    }
    fn = routes.get(p)
    if not fn:
        return None
    return json_response(fn())
