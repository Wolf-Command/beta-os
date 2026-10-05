# Spartacus schema dump plan (DDL only)

Generated: 2026-09-30T10:54:34+08:00
DB: `/Users/wolfterminal/.openclaw/personal/health/spartacus.sqlite`

## Counts

```json
{
  "body_log": 1,
  "contacts": 10,
  "days": 80,
  "food_log": 20,
  "habit_ticks": 2,
  "habits": 9,
  "journal": 0,
  "lift_sessions": 22,
  "lift_weights": 57,
  "metrics_log": 2,
  "peptide_log": 7,
  "plans": 79,
  "profile": 23,
  "pt141_log": 0,
  "quotes": 147,
  "reading_log": 0,
  "resets": 79,
  "sched_fired": 474,
  "training_log": 90,
  "water_log": 87,
  "weekly": 2
}
```

## DDL

```sql
CREATE TABLE profile (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE days (
  date TEXT PRIMARY KEY, day_num INTEGER,
  water_ml INTEGER DEFAULT 0,
  wo1_done INTEGER DEFAULT 0, wo1_outdoor INTEGER DEFAULT 0,
  wo2_done INTEGER DEFAULT 0, wo2_outdoor INTEGER DEFAULT 0,
  meditation_done INTEGER DEFAULT 0, reading_done INTEGER DEFAULT 0,
  diet_status TEXT DEFAULT '',
  logged_closed INTEGER DEFAULT 0, verdict TEXT DEFAULT '', reset_reason TEXT DEFAULT ''
, breathwork_done INTEGER DEFAULT 0, perfect INTEGER DEFAULT 0, card_msg_id INTEGER DEFAULT 0);
CREATE TABLE water_log (ts TEXT, date TEXT, ml INTEGER);
CREATE TABLE training_log (ts TEXT, date TEXT, lift TEXT, entry TEXT);
CREATE TABLE peptide_log (date TEXT, compound TEXT, status TEXT);
CREATE TABLE pt141_log (ts TEXT, month TEXT);
CREATE TABLE resets (date TEXT, day_num INTEGER, reason TEXT);
CREATE TABLE weekly (date TEXT PRIMARY KEY, weight REAL, waist REAL,
  knee_pain INTEGER, photo_file_id TEXT);
CREATE TABLE plans (date TEXT PRIMARY KEY, proposal TEXT,
  confirmed INTEGER DEFAULT 0, escalated INTEGER DEFAULT 0, defaulted INTEGER DEFAULT 0,
  cal_event_ids TEXT DEFAULT '', tasks TEXT DEFAULT '');
CREATE TABLE sched_fired (kind TEXT, date TEXT, PRIMARY KEY (kind, date));
CREATE TABLE contacts (date TEXT, name TEXT);
CREATE TABLE quotes (quote TEXT PRIMARY KEY, author TEXT, used_date TEXT);
CREATE TABLE journal (ts TEXT, date TEXT, kind TEXT, entry TEXT);
CREATE TABLE food_log (ts TEXT, date TEXT, item TEXT,
  kcal REAL DEFAULT 0, protein REAL DEFAULT 0, carbs REAL DEFAULT 0, fat REAL DEFAULT 0, source TEXT, fdc_id TEXT, grams REAL);
CREATE TABLE metrics_log (
  date TEXT PRIMARY KEY,
  sleep_hours REAL,
  sleep_quality INTEGER,
  rhr INTEGER,
  weight REAL,
  waist REAL,
  knee_pain INTEGER,
  notes TEXT DEFAULT ''
);
CREATE TABLE habits (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  active INTEGER DEFAULT 1,
  sort INTEGER DEFAULT 0
);
CREATE TABLE habit_ticks (
  habit_id TEXT NOT NULL,
  date TEXT NOT NULL,
  done INTEGER DEFAULT 1,
  PRIMARY KEY (habit_id, date)
);
CREATE TABLE reading_log (
  ts TEXT,
  date TEXT,
  book TEXT,
  pages INTEGER DEFAULT 0,
  note TEXT DEFAULT ''
, learnt TEXT DEFAULT '');
CREATE TABLE lift_weights (
  lift_key TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  equip TEXT NOT NULL,
  weight_kg REAL,
  updated TEXT,
  last_bump_week INTEGER,
  note TEXT DEFAULT ''
);
CREATE TABLE lift_sessions (
  date TEXT NOT NULL,
  lift_key TEXT NOT NULL,
  sets_json TEXT NOT NULL,
  progressed INTEGER DEFAULT 0,
  PRIMARY KEY (date, lift_key)
);
CREATE TABLE body_log (
  date TEXT PRIMARY KEY,
  ts TEXT,
  weight_kg REAL,
  age_y INTEGER,
  sf_chest_mm REAL,
  sf_abdomen_mm REAL,
  sf_thigh_mm REAL,
  sf_tricep_mm REAL,
  sf_subscap_mm REAL,
  sf_suprailiac_mm REAL,
  sf_midax_mm REAL,
  sf_bicep_mm REAL,
  sf_calf_mm REAL,
  g_neck_mm REAL,
  g_shoulders_mm REAL,
  g_chest_mm REAL,
  g_arm_mm REAL,
  g_forearm_mm REAL,
  g_waist_mm REAL,
  g_hips_mm REAL,
  g_thigh_mm REAL,
  g_calf_mm REAL,
  sf_sum_mm REAL,
  bd REAL,
  bf_pct REAL,
  notes TEXT DEFAULT ''
);

```

## Git policy

- DDL + counts: OK in `beta-os/state/.../transfer/`
- DB file / row dumps / PII: **FORBIDDEN**
