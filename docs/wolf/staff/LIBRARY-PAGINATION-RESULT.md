# LIBPAGE-1 — Library numbered pagination

Decision served: Haikal library human test, 28 Sep 2026 (LIBPAGE-1 in `docs/wolf/staff/HUMAN-COMMISSIONING-28SEP.md`). This extends the existing Content Library search. It is not a new system. Beta `:8788` only. Production `:8787` was not edited and was not restarted. No grant, role, or person was added. `staff_ready` and `human_commissioned` stay false. The Haikal search / find / download record in the commissioning note was not edited.

The library keeps the index total and asks the server for one page of 48. The address bar keeps the query, brand, filters, sort, and page. Page changes use `history.pushState`. Back and forward restore that state. A page past the end clamps to the last page. PREV and NEXT stay, and they are disabled at the ends. The current page is marked. The first and last page numbers stay visible, with the pages next to the current one, and an ellipsis where there is a gap. On a 390px width the window is shorter: neighbours of one page.

Haikal’s example sentence is the staff line. Atrium video search on page 3 reads `15,561 indexed files match · Showing 48 on this page`. The first Atrium page reads `32,608 indexed files match · Showing 49 on this page` because that page also includes one uploaded file beside the 48 indexed files. Download (ZIP) is unchanged.

## Proof

`scripts/tests/test_library_pagination_20260928.py` via `scripts/tests/run_guarded.py`: SUMMARY pass=53 fail=0.

Also via `run_guarded.py`, fail 0:

- `test_staff_access_20260928.py` — SUMMARY pass=274 fail=0
- `test_role_routing_20260928.py` — SUMMARY pass=84 fail=0
- `test_content_engine_staff_ux.py` — PASS=54 FAIL=0
- `test_content_engine_staff_shell_cleanup.py` — PASS=45 FAIL=0
- `test_content_engine_nas_library_round3.py` — PASS=19 FAIL=0
- `test_nas_estate_index.py` — PASS=59 FAIL=0
- `test_ggv_finance_nota_storage_accountant.py` — PASS=100 FAIL=0

Three suites did not finish green. They are not pagination regressions:

- `test_content_engine_haikal_fail_repair.py` and `test_content_engine_haikal_round2.py` call `ensure_registry` / `ensure_content_all_brands_scope` on the canonical catalog. Under the guard that write is refused (`sqlite3.DatabaseError: not authorized`). They were not pointed at a temp copy.
- `test_wolf_nas_library_upload_p0.py` — PASS=40 FAIL=17. The failures are `missing_auth` on live `:8788` (`cloudflare_access`). Auth mode was not switched.

Screenshots, Haikal subject, ephemeral handler, `development_assertion` on that handler only:

- `docs/wolf/staff/shots/library-pagination-desktop.png`
- `docs/wolf/staff/shots/library-pagination-phone.png`
- `docs/wolf/staff/shots/library-pagination-page3-desktop.png`

Phone measure: scroll width 390, client width 390, page button height 44. The harness answers preview image requests with a stand-in JPEG so the shot does not read the NAS. The counts and page numbers come from the index. Live `:8788` auth mode was not changed.

The listener pid and start time are recorded after the commit, in the working copy of this file, so the commit stays earlier than the process start.
