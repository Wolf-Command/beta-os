# GAP — Staff-safe provider naming (Wolf Intelligence surfaces)

**Opened:** 2026-10-02 · pack `BZG-CLOSE-VISION-CAPABILITY-1`  
**Status:** PARTIAL — Daily Close page addressed; Wolf Intelligence tool surfaces not yet audited.

## Rule
Operational staff must never see provider or API-key names (`Gemini`, `Anthropic`, `OpenAI`, `Claude`, `GPT-…`, `api_key`, authorisation errors). Staff copy:

> Receipt reading is temporarily unavailable. Retry or enter the figures manually.

Provider/key detail belongs in diagnostic logs and Owner technical evidence only.

## Done this pack
- `scripts/core/bzg_close_vision.py` — `_staff_sanitize` + `STAFF_VISION_UNAVAILABLE`
- `scripts/serve_beta.py` — `_staff_vision_sanitize` / VisionError soft path
- `dashboards/uma-blu-close.html` — `staffSafeVisionMsg` on extract/retry/manual paths

## Open gap (honest)
Wolf Intelligence tool desks / agent surfaces may still echo raw provider errors. Needs a separate audit pass before claiming staff-safe naming Wolf-wide. Do not block Daily Close vision fix on that sweep.
