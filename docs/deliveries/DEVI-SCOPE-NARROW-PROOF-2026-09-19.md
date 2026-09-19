# DEVI SCOPE NARROW PROOF — 2026-09-19

- **When (WITA):** 2026-09-19T08:51:31+08:00
- **Catalog:** `/Users/wolfterminal/beta-os/catalog/content_library.sqlite`
- **Backup:** `/Users/wolfterminal/beta-os/state/backups/content_library.sqlite.pre-devi-scope-narrow-20260919-085131`
- **Assignment:** `ASG-DEVI-HFB-UMA-1`
- **Ended:** `SCOPE-BZG-ENTITY` → status=`ENDED` end_at=`2026-09-19T08:51:31+08:00`
- **Kept ACTIVE:** `SCOPE-BZG-UMA`
- **Prove OK:** `True` (ACTIVE scopes must be exactly {SCOPE-BZG-UMA})

## BEFORE
```
{'assignment_id': 'ASG-DEVI-HFB-UMA-1', 'scope_id': 'SCOPE-BZG-ENTITY', 'status': 'ACTIVE', 'start_at': '2026-09-17T00:00:00+08:00', 'end_at': None}
{'assignment_id': 'ASG-DEVI-HFB-UMA-1', 'scope_id': 'SCOPE-BZG-UMA', 'status': 'ACTIVE', 'start_at': '2026-09-17T00:00:00+08:00', 'end_at': None}
```

## AFTER
```
{'assignment_id': 'ASG-DEVI-HFB-UMA-1', 'scope_id': 'SCOPE-BZG-ENTITY', 'status': 'ENDED', 'start_at': '2026-09-17T00:00:00+08:00', 'end_at': '2026-09-19T08:51:31+08:00'}
{'assignment_id': 'ASG-DEVI-HFB-UMA-1', 'scope_id': 'SCOPE-BZG-UMA', 'status': 'ACTIVE', 'start_at': '2026-09-17T00:00:00+08:00', 'end_at': None}
```

## SELECT proof
```sql
SELECT assignment_id, scope_id, status, start_at, end_at
FROM org_assignment_scopes
WHERE assignment_id = 'ASG-DEVI-HFB-UMA-1'
  AND status = 'ACTIVE' AND (end_at IS NULL OR end_at = '');
-- expect exactly one row: SCOPE-BZG-UMA
```

## ACTIVE rows (post)
```
{'assignment_id': 'ASG-DEVI-HFB-UMA-1', 'scope_id': 'SCOPE-BZG-UMA', 'status': 'ACTIVE', 'start_at': '2026-09-17T00:00:00+08:00', 'end_at': None}
```

