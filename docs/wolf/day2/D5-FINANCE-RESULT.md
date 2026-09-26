# D5 — Atrium Finance security and backup truth — 27 Sep 2026

Branch `wolf/foundation-20260926` in `/Users/wolfterminal/atrium-finance`. Not pushed. Production `:8787` stayed pid 15975. Beta `:8788` stayed pid 4443. Scratch servers on `:8791` and `:8792` were stopped after the checks. Human commissioned: no. Operating adoption: no.

These stay separate:

| Layer | This pack |
| --- | --- |
| TECHNICAL PROOF | `tsc` and `npm test` passed. Route table public set is health, login, logout. Local SHA256 of the backup file matches the restored file. |
| DEPLOYED ROUTE PROOF | Unsigned sweep of 135 routes on `:8791`. Restored database booted on `:8792` and returned the scratch marker. |
| STAFF READINESS | `scripts/start-fresh-commissioning.sh` and the commissioning checklist tell a person how to open a new database. |
| HUMAN COMMISSIONING | No. Nobody in a hotel role has signed this ledger off. |
| OPERATING ADOPTION | No. The scratch B2 object is not the hotel backup, and the books were not entered. |

## BEFORE

Atrium's own upload names were empty. No `.env`. Process environment had `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, and `B2_ENDPOINT` unset. `.env.example` has those four names with empty values. `scripts/com.atriumfinance.backup.plist` is in the repo and is not loaded. `restic` is not installed. The `b2` CLI is not installed. No `~/.b2_account_info`. No keychain item whose service, label, or server is Backblaze, restic, rclone, or b2.

What is present, by name only:

- rclone config `~/.config/rclone/rclone.conf` (983 bytes). Remotes: `b2` (type b2), `wolfb2` (type b2), `b2nas` (type b2), `wolfb2crypt` (type crypt), `r2`, `r2archive`.
- `rclone lsd b2:` listed bucket `wolf-cold-archive`.
- Loaded launchd labels: `com.wolfcommand.backup`, `com.wolfcommand.footage-b2-sync`, `com.wolfcommandsystem.b2-archive`, `com.wolfcommand.b2-archive-proof`, `com.wolfcommand.b2-cap-monitor`, `com.wolfcommandsystem.daily-backup`.
- `wolf-secrets.env` contains `B2_FOOTAGE_CRYPT_PASS` (set; footage crypt, not an atrium application key) and `ATRIUM_PREMIUM` (set; not a B2 key).

The retired password literal is gone from the working tree. It remains in older commits. Five other seed passwords from the same era are also gone from the working tree and remain in those older commits. Values are not written here.

`UserAccessManager` still prefilled a different password when creating a user.

## DONE

- Scratch backup of a fresh database through the existing rclone remote `b2`, then a restore and a boot on `:8792`.
- History of the retired literal and the five seed literals recorded by commit, file, and date. Hash check against existing databases printed match no. No live match in env or process environment. No rotation, because nothing current matched. Git history was not rewritten.
- Unsigned sweep: the only non-401 routes are the three public auth/health routes. No finance route was opened. No auth patch.
- New-user form no longer submits a prefilled password. A blank create is refused in the form.
- `scripts/start-fresh-commissioning.sh` creates the parent directory and starts the app only after the session secret and six `SEED_*_PASSWORD` names are set. Checklist updated.

## VERIFIED

Production and beta after the scratch servers were stopped:

```
Python 15975 127.0.0.1:8787
Python 4443  127.0.0.1:8788
8791 closed
8792 closed
```

### Backup

Fresh database `/tmp/atrium-d5-20260927/fresh.sqlite` (483328 bytes) after boot on `:8791` with random `SEED_*_PASSWORD` values that were not recorded. Controller login returned 200, role `role-financial-controller`, no `password` field. `POST /api/admin/settings` set `property_name` to `D5-SCRATCH-MARKER`, `room_count` 0, `base_currency` IDR, empty period lock.

Counts on that file: users 6, bcrypt length-60 hashes 6, plaintext passwords 0, accounts 37, journals 0, revenue 0, spending 0, owner units 0, service-charge employees 0, inventory items 0, tax rules 9 with 0 rates configured. Property name was blank before the marker write.

```
rclone copyto fresh.sqlite b2:wolf-cold-archive/atrium-finance-d5-scratch/atrium-d5-fresh.sqlite
copyto_exit 0
rclone ls b2:wolf-cold-archive/atrium-finance-d5-scratch
   483328 atrium-d5-fresh.sqlite
rclone hashsum SHA1 b2:wolf-cold-archive/atrium-finance-d5-scratch
25e4b3d6689678c96052414989adf7e18fbfb4ca  atrium-d5-fresh.sqlite
shasum -a 1 fresh.sqlite
25e4b3d6689678c96052414989adf7e18fbfb4ca  fresh.sqlite
```

`rclone hashsum SHA256` and `rclone hashsum MD5` on that remote returned `hash type not supported`. Local SHA256 of the source and of the restored file:

```
58b125529880e4795c7013bb62fbb8cb63ec47a87ed37a05509e04028d84f248  fresh.sqlite
58b125529880e4795c7013bb62fbb8cb63ec47a87ed37a05509e04028d84f248  restored.sqlite
cmp identical yes
```

Restored file booted with `PORT=8792` and `DATABASE_FILE=/tmp/atrium-d5-20260927/restored.sqlite`.

```
login_status 200
settings_status 200
property_name D5-SCRATCH-MARKER
room_count 0
base_currency IDR
period_lock_date ''
journals_unsigned 401
journals_signed 200
journal_count 0
```

That object is a test database. It is not the hotel ledger. The atrium script's four names are still unset, so `backup-status.json` was not written and the screen still has no atrium backup timestamp.

### Git-history password

The fallback literal (not printed) was the empty-password substitute in `server/store.ts`:

| Commit | Date | Files |
| --- | --- | --- |
| `54ac7de` | 2026-09-20T03:13:54+08:00 | `server/store.ts` user-save fallback; `src/components/auth/LoginScreen.tsx` prefill and submit fallback |
| `f2483b7` | 2026-09-22T13:43:58+08:00 | same two files |
| `480c8e7` | 2026-09-24T09:17:49+08:00 | same two files |
| `9f854bf` | 2026-09-25T10:27:06+08:00 | same two files |
| `7095938` | 2026-09-26T00:17:01+08:00 | same two files. Last copy in `LoginScreen.tsx` |
| `dd090d1` | 2026-09-26T00:38:15+08:00 | `server/store.ts` `hashPassword` fallback; `tests/auth.test.ts` |
| `c28a122` | 2026-09-26T00:55:52+08:00 | `server/store.ts` `hashPassword` fallback. Gone from the test |
| `85e0e00` | 2026-09-26T01:28:22+08:00 | `server/store.ts` lines that hash `current \|\| <literal>` and hash the literal on save |
| `b4f800e` | 2026-09-27T02:54:16+08:00 | removed. Working tree does not contain it |

Five role seed literals (not printed) were `password: '<literal>'` on `usr-controller-1`, `usr-accountant-1`, `usr-front-desk-1`, `usr-ap-buyer-1`, and `usr-gm-1` in `server/store.ts` and `tests/auth.test.ts` at `54ac7de`, `f2483b7`, `480c8e7`, `9f854bf`, `7095938`, and `dd090d1`. `c28a122` has zero quoted password assignments. They are not in the working tree.

Hash check, match yes/no only:

| Database | Users | Hash match |
| --- | ---: | --- |
| `data/uncommissioned/atrium.sqlite` | 0 | no |
| `data/uncommissioned/atrium.sqlite-wal` | — | bytes no |
| `/tmp/atrium-sprint7-20260927/app.sqlite` | 6, all bcrypt | no |
| `data/owner_pool.json`, `data/owner_email_store.json` | — | bytes no |

`.env` absent. `.env.example` match no. `wolf-secrets.env` match no. Shell environment match no. Other process environments match no. No atrium-finance server was listening on `:8787` or `:8788` (those are the Wolf Python dashboards). No local rotation was done. History was not rewritten.

The same fallback plaintext is still in `docs/wolf/sprint7/P2-FINANCE-RESULT.md` in beta-os. That file is not a login database.

The create-user default in `UserAccessManager.tsx` was a different literal, still in HEAD, and was not one of the six above. It is removed. New users must type a password.

### Unsigned routes

`:8791`, no cookie, 135 routes from `server.ts` and `server/auth.ts`:

```
routeCount 135
401: 132
200: 2
400: 1
GET /api/not-a-finance-route: 401
```

| Method | Path | Status | Why |
| --- | --- | ---: | --- |
| GET | `/api/health` | 200 | Public liveness check. `isPublicApi` and route kind `public`. Body was `{"status":"ok",...}`. |
| POST | `/api/auth/login` | 400 | Public sign-in. Body `{}` fails the login schema before any session: `email: Required`, `password: Required`. |
| POST | `/api/auth/logout` | 200 | Public so a browser can clear `amg.sid`. Empty body is valid. Body was `{"ok":true}`. |

No other route returned anything but 401. No finance payload was returned. No code change and no new test: the three exemptions were already the intended public set.

### Commissioning script

```
PORT=8787 → exit 1, "Refusing PORT=8787"
DATABASE_FILE=.../data/uncommissioned/atrium.sqlite → exit 1
clean environment, PORT=8790 → exit 1, lists SESSION_SECRET and the six SEED_*_PASSWORD names
```

### Tests

`npx tsc --noEmit --pretty false` exited 0.

`npm test`:

```
ℹ tests 10
ℹ pass 10
ℹ fail 0
ℹ skipped 0
ℹ duration_ms 3999.026458
```

## WAITING HUMAN

- Set `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, and `B2_ENDPOINT` if the atrium nightly script should upload. Load `scripts/com.atriumfinance.backup.plist` only after those names are set. Bucket lifecycle (delete objects older than 30–90 days) is a B2 dashboard setting.
- The scratch object `b2:wolf-cold-archive/atrium-finance-d5-scratch/atrium-d5-fresh.sqlite` was left in place. Delete it only if you do not want the test file kept.
- The retired literal is still in git history and in `docs/wolf/sprint7/P2-FINANCE-RESULT.md`. History was not rewritten. Redacting the markdown file is a human choice.
- Sign in on a new database with the script below. This pack did not commission the ledger.

## BLOCKERS

- The in-app backup line stays "No backup recorded" until the four atrium names exist and an upload writes `backup-status.json`. The rclone scratch object does not flip that line.
- Seed addresses remain `*@seed.invalid` until a Financial Controller replaces them.
- `data/owner_pool.json` and `data/owner_email_store.json` are still the old generated sample. Do not import them.

## NEXT HUMAN TEST

1. Confirm nothing is listening on `:8791` or `:8792`.
2. In `/Users/wolfterminal/atrium-finance`, set `SESSION_SECRET` and the six `SEED_*_PASSWORD` values in the shell. Do not commit them.
3. `export PORT=8790` and `export DATABASE_FILE="$PWD/data/commissioning/atrium.sqlite"`.
4. `zsh scripts/start-fresh-commissioning.sh`.
5. Open `http://127.0.0.1:8790`. Financial Controller signs in at `controller@seed.invalid` and saves the real property name, room count, and currency. Leave the period lock empty.
6. Each of the other five roles signs in and confirms a locked pillar. Do not type sample hotel figures.
7. Checklist: `docs/wolf/sprint7/ATRIUM-FINANCE-COMMISSIONING-CHECKLIST.md`.

RESULT: PASS
