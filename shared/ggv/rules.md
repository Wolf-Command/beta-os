# GGV Content Engine 2.0 — Rules

**Workspace:** `/Users/wolfterminal/beta-os/` only.  
**Isolation:** Do not read, write, or route through legacy `/wolf-system`.

## Naming Law (LOCKED)

Format:

```text
brand_drop_STAGE_type_slug_YYYYMMDD
```

### Active brands
- `habitat`
- `umablu`
- `atrium`
- `selo`
- `tropik`

### STAGE
- `RAW` — ingested, not yet catalog-final
- `FINAL` — cataloged / rendered ready assets

### Type
- `video`
- `audio`
- `broll`
- `graphic`

### Examples
- `habitat_drop_RAW_video_lobby-walkthrough_20260914`
- `umablu_drop_FINAL_graphic_menu-board_20260914`

## Paths
- Shared GGV standards: `shared/ggv/`
- Catalog DB: `catalog/content_library.sqlite`
- Media RAW: `library_v2/RAW/`
- Media FINAL: `library_v2/FINAL/`
- Draft schedules: `private/content_planner/`
- Dashboards 2.0: `dashboards/`

## Status values (assets table)
- `indexed`
- `ready_for_edit`
- `archived`

## Footage Naming Law (LOCKED 15 Sep 2026)

Structure:

```text
brand_STAGE_type_subject_detail_YYYYMMDD_seq.ext
```

Examples:
- `habitat_RAW_video_villa-pool_wide_20260915_001.mp4`
- `habitat_RAW_video_villa-pool_closeup_20260915_002.mp4`
- `selo_RAW_video_selong-belanak-beach_drone-wide_20260915_001.mp4`

### STAGE
- `RAW` — original from camera/phone/drone
- `EDIT` — working edit
- `FINAL` — finished approved asset

### Sequence
- RAW clips of the same subject: `_001`, `_002`, `_003` (separate clips)
- EDIT/FINAL versions of the same content: `_v01`, `_v02`, `_v03`

### Product rule
Users give Content Engine simple shoot info; **Content Engine generates Wolf filenames**. Do not require manual rename of camera originals.

### Batch upload (intended UX — not all built yet)
Enter once for the batch: brand, stage, subject (and optional location/talent).
Per clip: detail (wide/closeup/drone/…), sequence.
Prefer describe after thumbnails when practical.

Legacy `brand_drop_STAGE_type_slug_YYYYMMDD` remains accepted for older staged assets until migrate.

