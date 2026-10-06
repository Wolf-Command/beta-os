"""Fail-closed paid spend gate (Owner order 2026-10-06 08:33). Provider calls are mocked."""
from __future__ import annotations

# --- State isolation (Vesper M1): before any wolf_intelligence import ---------
import atexit as _atexit
import os as _os
import shutil as _shutil
import sys as _sys
import tempfile as _tempfile

if not _os.environ.get("WI_TEST_STATE_ISOLATED"):
    if "wolf_intelligence.paths" in _sys.modules:
        raise RuntimeError("wolf_intelligence.paths imported before test state isolation")
    _os.environ["WI_TEST_CONFIGURED_STATE_ROOT"] = _os.environ.get("WOLF_INTELLIGENCE_STATE_ROOT", "")
    _TEST_STATE_ROOT = _tempfile.mkdtemp(prefix="wi-test-state-")
    _os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = _TEST_STATE_ROOT
    _os.environ["WI_TEST_STATE_ISOLATED"] = _TEST_STATE_ROOT
    _os.environ.pop("WOLF_INTELLIGENCE_CONFIG_MIRROR", None)
    _atexit.register(_shutil.rmtree, _TEST_STATE_ROOT, True)
# -----------------------------------------------------------------------------

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from wolf_intelligence import paths
from wolf_intelligence.adapters import live_gate
from wolf_intelligence.adapters.live_gate import (
    DAILY_COST_ENV,
    LIVE_SUBMIT_ENV,
    MAX_COST_ENV,
    OWNER_ACTION_REQUIRED,
    PROVIDER_MOCK_ENV,
    SpendDenied,
    cost_cap,
    daily_ceiling,
    enforce_cost_cap,
    parse_usd,
    per_call_cap,
)


def _guard(root: Path) -> None:
    """Same rule as test_hardening: derived from the configured live root, temp only."""
    root = Path(root).resolve()
    lives = [Path(paths.LIVE_STATE_ROOT).resolve()]
    configured = os.environ.get("WI_TEST_CONFIGURED_STATE_ROOT", "").strip()
    if configured:
        lives.append(Path(configured).expanduser().resolve())
    for live in lives:
        if root == live or root.is_relative_to(live) or live.is_relative_to(root):
            raise RuntimeError("refusing to run tests against live Wolf Intelligence state")
    if not root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise RuntimeError("refusing to run tests outside the system temp dir")


_guard(paths.STATE_ROOT)

# Every bad value the Owner listed. (label, value, expected reason code)
BAD_AMOUNTS = [
    ("missing", None, "missing"),
    ("blank", "", "blank"),
    ("blank_spaces", "   ", "blank"),
    ("zero_str", "0", "zero"),
    ("zero_num", 0, "zero"),
    ("zero_float", 0.0, "zero"),
    ("negative_str", "-1", "negative"),
    ("negative_num", -0.01, "negative"),
    ("text", "abc", "not_a_number"),
    ("text_dollar", "$5", "not_a_number"),
    ("text_comma", "1,000", "not_a_number"),
    ("nan_str", "nan", "nan"),
    ("nan_str_upper", "NaN", "nan"),
    ("nan_float", float("nan"), "nan"),
    ("inf_str", "inf", "infinite"),
    ("infinity_str", "Infinity", "infinite"),
    ("neg_infinity_str", "-Infinity", "infinite"),
    ("inf_float", float("inf"), "infinite"),
    ("neg_inf_float", float("-inf"), "infinite"),
    ("overflow_1e309", "1e309", "infinite"),
    ("over_sanity_max", "1000.01", "over_sanity_max"),
    ("over_sanity_max_num", 5000, "over_sanity_max"),
    ("huge_finite", "1e300", "over_sanity_max"),
    ("type_list", [1], "wrong_type"),
    ("type_dict", {"usd": 1}, "wrong_type"),
    ("type_bool_true", True, "wrong_type"),
    ("type_bool_false", False, "wrong_type"),
]


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self._env = os.environ.copy()
        self.tmp = tempfile.TemporaryDirectory()
        self._ledger = paths.LEDGER_DIR
        paths.LEDGER_DIR = Path(self.tmp.name) / "ledger"
        paths.LEDGER_DIR.mkdir()
        for k in (LIVE_SUBMIT_ENV, MAX_COST_ENV, DAILY_COST_ENV, PROVIDER_MOCK_ENV,
                  "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
            os.environ.pop(k, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)
        paths.LEDGER_DIR = self._ledger
        self.tmp.cleanup()

    def price_table(self, mutate=None, *, verified: bool = True, raw: str | None = None) -> Path:
        out = Path(self.tmp.name) / "prices.json"
        if raw is not None:
            out.write_text(raw, encoding="utf-8")
            return out
        data = json.loads(live_gate.PRICE_CEILINGS_PATH.read_text(encoding="utf-8"))
        for entry in data["models"].values():
            entry["verified"] = verified
        if mutate:
            mutate(data)
        out.write_text(json.dumps(data), encoding="utf-8")
        return out

    def owner_caps(self, per_call="1.0", daily="1.0") -> None:
        os.environ[MAX_COST_ENV] = per_call
        os.environ[DAILY_COST_ENV] = daily

    def gate(self, job=None, *, table: Path | None = None, model="gpt-4o-mini"):
        table = table or self.price_table()
        with mock.patch.object(live_gate, "PRICE_CEILINGS_PATH", table):
            return enforce_cost_cap(job or {}, model_id=model, prompt="tiny", max_output_tokens=64)

    def assertDenied(self, result, code: str) -> None:
        refusal = result[0]
        self.assertIsNotNone(refusal, f"expected denial {code}")
        self.assertEqual(refusal.status, "GATED")
        self.assertTrue(refusal.message.startswith(OWNER_ACTION_REQUIRED), refusal.message)
        self.assertEqual(refusal.data["reason_code"], code)
        self.assertTrue(refusal.data["owner_action_required"])
        self.assertFalse(refusal.data["provider_called"])


class ParseUsdTests(_Base):
    def test_every_bad_amount_is_denied_with_its_reason(self) -> None:
        for label, value, code in BAD_AMOUNTS:
            with self.subTest(label=label):
                with self.assertRaises(SpendDenied) as ctx:
                    parse_usd(value, what="cap", sanity_max=1000.0)
                self.assertEqual(ctx.exception.code, code)

    def test_good_amounts(self) -> None:
        self.assertEqual(parse_usd("0.02", what="cap", sanity_max=1000.0), 0.02)
        self.assertEqual(parse_usd(1000, what="cap", sanity_max=1000.0), 1000.0)
        self.assertEqual(parse_usd(" 5 ", what="cap", sanity_max=1000.0), 5.0)


class OwnerPerCallCapTests(_Base):
    def test_env_cap_bad_values_deny(self) -> None:
        os.environ[DAILY_COST_ENV] = "1.0"
        for label, value, code in BAD_AMOUNTS:
            if not isinstance(value, (str, type(None))):
                continue  # env values are strings or absent
            with self.subTest(label=label):
                if value is None:
                    os.environ.pop(MAX_COST_ENV, None)
                else:
                    os.environ[MAX_COST_ENV] = value
                self.assertDenied(self.gate(), code)
                self.assertIsNone(cost_cap({}))

    def test_job_cap_bad_values_deny(self) -> None:
        self.owner_caps()
        for label, value, code in BAD_AMOUNTS:
            if value is None:
                continue  # an absent job cap falls back to the Owner cap
            with self.subTest(label=label):
                self.assertDenied(self.gate({"max_cost_usd": value}), code)
                self.assertIsNone(cost_cap({"max_cost_usd": value}))

    def test_job_cap_cannot_raise_owner_cap(self) -> None:
        self.owner_caps(per_call="0.001")
        self.assertEqual(per_call_cap({"max_cost_usd": 500}), 0.001)
        self.assertEqual(per_call_cap({"max_cost_usd": "0.0005"}), 0.0005)

    def test_job_cap_without_owner_cap_denies(self) -> None:
        os.environ[DAILY_COST_ENV] = "1.0"
        self.assertDenied(self.gate({"max_cost_usd": 0.5}), "missing")

    def test_cap_must_declare_usd(self) -> None:
        self.owner_caps()
        self.assertDenied(self.gate({"max_cost": 0.5}), "currency_missing")
        self.assertDenied(self.gate({"max_cost_usd": 0.5, "max_cost_currency": "EUR"}), "currency_missing")
        self.assertDenied(self.gate({"max_cost_usd": 0.5, "max_cost_currency": None}), "currency_missing")
        self.assertIsNone(self.gate({"max_cost_usd": 0.5, "max_cost_currency": "USD"})[0])


class DailyCeilingTests(_Base):
    def test_daily_missing_or_invalid_denies(self) -> None:
        os.environ[MAX_COST_ENV] = "1.0"
        for label, value, code in BAD_AMOUNTS:
            if not isinstance(value, (str, type(None))):
                continue
            with self.subTest(label=label):
                if value is None:
                    os.environ.pop(DAILY_COST_ENV, None)
                else:
                    os.environ[DAILY_COST_ENV] = value
                self.assertDenied(self.gate(), code)

    def test_daily_default_is_blocked(self) -> None:
        os.environ.pop(DAILY_COST_ENV, None)
        with self.assertRaises(SpendDenied):
            daily_ceiling()

    def _ledger_line(self, **rec) -> None:
        day = datetime.now(ZoneInfo("Asia/Makassar")).strftime("%Y-%m-%dT10:00:00+08:00")
        row = {"at": day, "pool_id": "openai_api", "provider_called": True, "metered_usd": 0.0}
        row.update(rec)
        with (paths.LEDGER_DIR / "ledger.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    def test_daily_metered_ceiling_counts_today(self) -> None:
        self.owner_caps(per_call="1.0", daily="0.5")
        self.assertIsNone(self.gate()[0])
        self._ledger_line(metered_usd=0.5)
        self.assertDenied(self.gate(), "over_daily")

    def test_unknown_metered_spend_today_denies(self) -> None:
        self.owner_caps()
        self._ledger_line(metered_usd="UNKNOWN")
        self.assertDenied(self.gate(), "metered_unknown")

    def test_other_days_and_unpaid_pools_do_not_count(self) -> None:
        self.owner_caps(per_call="1.0", daily="0.01")
        self._ledger_line(at="2020-01-01T10:00:00+08:00", metered_usd=99)
        self._ledger_line(pool_id="ollama_local", metered_usd=99)
        self._ledger_line(provider_called=False, metered_usd=99)
        self.assertIsNone(self.gate()[0])

    def test_corrupt_ledger_denies(self) -> None:
        self.owner_caps()
        (paths.LEDGER_DIR / "ledger.jsonl").write_text("{not json\n", encoding="utf-8")
        self.assertDenied(self.gate(), "ledger_corrupt")


class PriceTableTests(_Base):
    def test_shipped_table_is_unverified_and_denies(self) -> None:
        data = json.loads(live_gate.PRICE_CEILINGS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["currency"], "USD")
        self.assertEqual(data["unit_tokens"], 1000000)
        self.assertTrue(data["models"])
        self.assertTrue(all(entry.get("verified") is False for entry in data["models"].values()))
        self.owner_caps()
        self.assertDenied(self.gate(table=live_gate.PRICE_CEILINGS_PATH), "price_unverified")

    def test_verified_must_be_true_boolean(self) -> None:
        self.owner_caps()
        def stringy(d):
            d["models"]["gpt-4o-mini"]["verified"] = "true"
        self.assertDenied(self.gate(table=self.price_table(stringy)), "price_unverified")
        def missing(d):
            d["models"]["gpt-4o-mini"].pop("verified")
        self.assertDenied(self.gate(table=self.price_table(missing)), "price_unverified")

    def test_corrupt_or_unparsable_config_denies(self) -> None:
        self.owner_caps()
        for label, raw in (("truncated", '{"currency": "USD", "models": {'), ("empty", ""), ("garbage", "\x00\x01"),
                           ("list", "[]"), ("no_models", '{"currency": "USD", "unit_tokens": 1000000}')):
            with self.subTest(label=label):
                self.assertDenied(self.gate(table=self.price_table(raw=raw)), "price_config_corrupt")
        self.assertDenied(self.gate(table=Path(self.tmp.name) / "missing.json"), "price_config_unreadable")

    def test_currency_and_units_required(self) -> None:
        self.owner_caps()
        cases = [
            ("no_currency", lambda d: d.pop("currency"), "currency_missing"),
            ("eur", lambda d: d.update(currency="EUR"), "currency_missing"),
            ("no_units", lambda d: d.pop("unit_tokens"), "units_missing"),
            ("wrong_units", lambda d: d.update(unit_tokens=1000), "units_missing"),
            ("units_text", lambda d: d.update(unit_tokens="1000000"), "units_missing"),
        ]
        for label, mutate, code in cases:
            with self.subTest(label=label):
                self.assertDenied(self.gate(table=self.price_table(mutate)), code)

    def test_bad_prices_deny(self) -> None:
        self.owner_caps()
        for label, value, code in BAD_AMOUNTS:
            if code == "over_sanity_max":
                continue  # price sanity max differs (per 1M tokens); covered below
            with self.subTest(label=label):
                def mutate(d, v=value):
                    d["models"]["gpt-4o-mini"]["input"] = v
                self.assertDenied(self.gate(table=self.price_table(mutate)), code)
        def huge(d):
            d["models"]["gpt-4o-mini"]["output"] = 1e6
        self.assertDenied(self.gate(table=self.price_table(huge)), "over_sanity_max")

    def test_bad_estimator_parameters_deny(self) -> None:
        self.owner_caps()
        for label, key, value in (("safety_nan", "safety_factor", float("nan")), ("safety_low", "safety_factor", 0.5),
                                  ("safety_text", "safety_factor", "1.5"), ("bytes_zero", "input_bytes_per_token", 0),
                                  ("overhead_neg", "input_overhead_tokens", -1), ("overhead_bool", "input_overhead_tokens", True)):
            with self.subTest(label=label):
                self.assertDenied(self.gate(table=self.price_table(lambda d, k=key, v=value: d.update({k: v}))),
                                  "price_config_invalid")

    def test_unknown_model_denies(self) -> None:
        self.owner_caps()
        self.assertDenied(self.gate(model="gpt-imaginary-9"), "unknown_model")

    def test_over_cap_denies(self) -> None:
        self.owner_caps(per_call="0.0000001")
        self.assertDenied(self.gate(), "over_cap")

    def test_all_valid_allows(self) -> None:
        self.owner_caps(per_call="0.05", daily="0.10")
        refusal, cap, estimate = self.gate()
        self.assertIsNone(refusal)
        self.assertEqual(cap, 0.05)
        self.assertTrue(0 < estimate <= cap)


class NoUnlimitedPathTests(_Base):
    def test_adapters_never_call_when_denied(self) -> None:
        from wolf_intelligence.adapters.anthropic_worker import AnthropicAPIAdapter
        from wolf_intelligence.adapters.gemini import GeminiAdapter
        from wolf_intelligence.adapters.openai_worker import OpenAIAPIAdapter
        os.environ[LIVE_SUBMIT_ENV] = "1"
        os.environ["OPENAI_API_KEY"] = "unit-test-openai-key"
        os.environ["ANTHROPIC_API_KEY"] = "unit-test-anthropic-key"
        os.environ["GEMINI_API_KEY"] = "unit-test-gemini-key"
        with mock.patch("wolf_intelligence.adapters.live_gate.urllib.request.urlopen") as opened:
            for env_cap in (None, "", "0", "-1", "nan", "inf", "-Infinity", "1e309", "1001", "abc"):
                if env_cap is None:
                    os.environ.pop(MAX_COST_ENV, None)
                else:
                    os.environ[MAX_COST_ENV] = env_cap
                for adapter in (OpenAIAPIAdapter(), AnthropicAPIAdapter(), GeminiAdapter()):
                    with self.subTest(env_cap=env_cap, worker=adapter.worker_id):
                        result = adapter.submit({"execute": True, "prompt": "tiny"})
                        self.assertEqual(result.status, "GATED")
                        self.assertTrue(result.message.startswith(OWNER_ACTION_REQUIRED))
                        self.assertFalse(result.data.get("provider_called"))
            # Valid caps but the shipped (unverified) price table: still denied.
            self.owner_caps()
            for adapter in (OpenAIAPIAdapter(), AnthropicAPIAdapter(), GeminiAdapter()):
                with self.subTest(worker=adapter.worker_id, case="unverified_prices"):
                    result = adapter.submit({"execute": True, "prompt": "tiny"})
                    # Gemini is stricter since the 09:39 order: the billing-unverified check in gemini_spend_gate
                    # fires before the price check, so it reports billing_unverified (still GATED, no call).
                    want = "billing_unverified" if adapter.worker_id == "gemini" else "price_unverified"
                    self.assertEqual(result.data.get("reason_code"), want)
                    self.assertEqual(result.status, "GATED")
            opened.assert_not_called()

    def test_live_submit_stays_off_by_default(self) -> None:
        from wolf_intelligence.adapters.openai_worker import OpenAIAPIAdapter
        os.environ.pop(LIVE_SUBMIT_ENV, None)
        with mock.patch("wolf_intelligence.adapters.live_gate.urllib.request.urlopen") as opened:
            self.assertEqual(OpenAIAPIAdapter().submit({"execute": True, "prompt": "tiny"}).status, "LIVE_DISABLED")
        opened.assert_not_called()


class TestGuardTests(unittest.TestCase):
    def test_guard_is_derived_from_configured_live_root(self) -> None:
        with self.assertRaises(RuntimeError):
            _guard(paths.LIVE_STATE_ROOT)
        with self.assertRaises(RuntimeError):
            _guard(Path(paths.LIVE_STATE_ROOT) / "events")
        with tempfile.TemporaryDirectory() as moved:
            with mock.patch.dict(os.environ, {"WI_TEST_CONFIGURED_STATE_ROOT": moved}):
                with self.assertRaises(RuntimeError):
                    _guard(Path(moved))
        with self.assertRaises(RuntimeError):
            _guard(Path.home() / "wolf-state" / "wolf-intelligence")  # not a temp dir
        _guard(paths.STATE_ROOT)  # the isolated test root passes

    def test_hardening_guard_matches(self) -> None:
        import importlib
        mod = _sys.modules.get("wolf_intelligence.tests.test_hardening") or _sys.modules.get("test_hardening")
        if mod is None:
            mod = importlib.import_module("wolf_intelligence.tests.test_hardening")
        with self.assertRaises(RuntimeError):
            mod.assert_test_state_root_is_safe(paths.LIVE_STATE_ROOT)
        mod.assert_test_state_root_is_safe(paths.STATE_ROOT)


if __name__ == "__main__":
    unittest.main()
