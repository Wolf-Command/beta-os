# Exception / Override Governance — Canon (Wolf Core)

**LOCKED 2026-09-17.**

EXCEPTION ≠ COMPLIANCE.

Normal control failure is preserved as the normal result. An authorised exception is a separate path (`ALLOWED_UNDER_EXCEPTION`) that never rewrites FAIL → PASS.

No exception unless explicitly granted. Matt Person (`PERS-MATT`) only may authorise/revoke until policy changes — not email, not ROLE alone. Delegation from Matt cannot authorise. Client force/override/skip flags are ignored.

Non-exceptionable controls cannot be overridden (authentication, Entity isolation, audit recording, attribution immutability, production sacred, controls marked `exceptionable=0`).

Evidence and SoD gates may proceed under an exception bound to that exact control reference only. One exception never covers both EVIDENCE_REQUIREMENT and SOD_CONSTRAINT.

Live exceptions = 0 until Matt creates an operational one separately. Mechanism BUILT; operational exceptions not seeded.
