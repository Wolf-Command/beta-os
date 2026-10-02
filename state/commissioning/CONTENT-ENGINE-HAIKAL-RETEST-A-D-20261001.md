# Haikal RETEST A–D — Content Upload + Library Search + Cancel
Issued: 2026-10-01T16:21:35+0800  
Updated: 2026-10-02 (CE-CANCEL-UPLOAD-1 folded in)  
Engineering: e0896ae + 9df3910 + CE-CANCEL-UPLOAD-1 on Beta :8788. staff_ready=false until PASS.

## TEST A — UPLOAD
Hard-refresh Content Engine on Beta. Upload 1–3 **new** real videos with Brand + details. Confirm they complete (preview miss must say Retry Preview, not whole-upload failed).

## TEST B — FIND THEM
Library → select that Brand → search a distinctive word from the detail → optionally add shoot month/date → find the new assets.

## TEST C — SEARCH BEHAVIOUR
Same search with different capitalisation (Pool/pool/POOL). Clear Brand → search still across authorised brands. Clear all filters → back to all authorised footage. Empty search must not show nothing.

## TEST D — NORMAL WORK
If A–C PASS: one normal real-world batch + use Library normally.

## TEST E — CANCEL UPLOAD (Haikal feedback · Owner-approved)
1. Start a small **3-file** upload.
2. Click **Cancel Upload** while it is running (one confirm: Cancel remaining uploads?).
3. Confirm remaining files stop correctly.
4. Confirm files that already finished remain in the Library (not deleted).
5. Summary should look like counts (uploaded / stopped / cancelled) — not a bare “Cancelled”.

## TEST F — STAGE / DETAILS CORRECTION (no re-upload)
1. Start an upload with a deliberately **wrong Stage** (or wrong brand/details).
2. After it lands in Library, open the asset → **Correct details**.
3. Fix Stage (and/or brand, content type, subject, location, details).
4. Confirm search/filter reflects the correction.
5. Confirm the file was **not** re-uploaded (same media; details only).

Report: **PASS** or the exact staff message you see.
Do not diagnose. Leave old BBQ batch alone (12 known on NAS; 2 of the reported 14 remain UNKNOWN).

**Content Upload remains uncommissioned** until A–F pass human testing. `staff_ready=false`.
