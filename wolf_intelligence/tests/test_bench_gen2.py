"""Gen-2 benchmark pack self-tests: every grader gives the computed reference 1.0, known-wrong answers score lower,
critical semantic failures are flagged, and the tie rule is the one declared before the run."""
import json
import unittest

from wolf_intelligence.real_bench.gen2 import (stats, t_coding, t_debug, t_extract, t_finance, t_largectx, t_planning,
                                               t_regression, t_security, t_ux, t_vision)


class Gen2Graders(unittest.TestCase):
    def test_references_score_full(self):
        self.assertEqual(t_coding.grade(t_coding.REFERENCE)["quality_score"], 1.0)
        self.assertEqual(t_debug.grade(t_debug.REFERENCE)["quality_score"], 1.0)
        self.assertEqual(t_security.grade(t_security.REFERENCE)["quality_score"], 1.0)
        self.assertEqual(t_finance.grade(t_finance.reference())["quality_score"], 1.0)
        self.assertEqual(t_extract.grade(t_extract.REFERENCE)["quality_score"], 1.0)
        self.assertEqual(t_planning.grade(t_planning.reference())["quality_score"], 1.0)
        self.assertEqual(t_regression.grade(t_regression.reference())["quality_score"], 1.0)
        self.assertEqual(t_largectx.grade(t_largectx.reference())["quality_score"], 1.0)
        self.assertEqual(t_vision.grade(t_vision.reference())["quality_score"], 1.0)

    def test_regression_critical_failures(self):
        e = t_regression.expected()
        e["B"]["bill_count"] = e["B"]["avg_per_bill"]                       # average confused with count
        e["C"]["payments"] = [p for p in e["C"]["payments"] if p["raw_label"] != "QRIS Mandiri"]  # unknown dropped
        g = t_regression.grade(json.dumps(e))
        self.assertTrue(g["critical_failure"])
        self.assertLessEqual(g["quality_score"], 0.5)
        e = t_regression.expected()
        for p in e["C"]["payments"]:
            if p["raw_label"] == "Debit BCA":
                p["classification"] = "CARD_DEBIT"                           # guessed instead of UNKNOWN
        self.assertTrue(t_regression.grade(json.dumps(e))["critical_failure"])
        e = t_regression.expected()
        e["A"]["bill_count"] = 9                                             # taken from DISCOUNT DETAIL section
        self.assertTrue(t_regression.grade(json.dumps(e))["critical_failure"])

    def test_wrong_answers_score_lower(self):
        self.assertLess(t_finance.grade(t_finance.reference().replace('"T08"', '"T02"'))["quality_score"], 1.0)
        self.assertLess(t_extract.grade(t_extract.REFERENCE.replace("7298250", "7339500"))["quality_score"], 1.0)
        naive = "```python\ndef parse_idr(text):\n    return int(text.replace('Rp','').replace('.','').strip())\n```"
        self.assertLess(t_coding.grade(naive)["quality_score"], 0.6)
        fp = t_security.REFERENCE.replace("]}", ',{"function":"list_orders","category":"SQL injection"}]}')
        self.assertLess(t_security.grade(fp)["quality_score"], 1.0)
        self.assertEqual(t_ux.deterministic('{"permissions": {}}')["score"], 0.0)

    def test_unsafe_code_not_executed(self):
        g = t_coding.grade("```python\nimport os\ndef parse_idr(t):\n    os.system('true')\n```")
        self.assertEqual(g["quality_score"], 0.0)
        self.assertIn("unsafe", g["failure_mode"])

    def test_planning_validator_rejects_violations(self):
        ref = json.loads(t_planning.reference())
        ref["schedule"]["E"]["who"] = ref["schedule"]["D"]["who"]            # two-person rule
        ref["schedule"]["E"]["start"] = ref["schedule"]["E"]["end"] = ref["schedule"]["D"]["start"]
        g = t_planning.grade(json.dumps(ref))
        self.assertFalse(g["details"]["valid"])

    def test_tie_rule(self):
        a = {"status": "SUPPORTED", "n": 3, "mean": 0.90, "sd": 0.0, "failure_rate": 0, "latency_ms_median": 9000}
        b = {"status": "SUPPORTED", "n": 3, "mean": 0.87, "sd": 0.0, "failure_rate": 0, "latency_ms_median": 1000}
        L = stats.leader({"slow": a, "fast": b})
        self.assertEqual(L["confidence"], "TIE")       # 0.03 <= 0.05 floor: latency may not create a quality win
        self.assertIsNone(L["leader"])
        b["mean"] = 0.70
        L = stats.leader({"slow": a, "fast": b})
        self.assertEqual(L["leader"], "slow")           # material quality gap: latency ignored
        noisy = {"status": "SUPPORTED", "n": 3, "mean": 0.80, "sd": 0.15, "failure_rate": 0.33, "latency_ms_median": 1}
        L = stats.leader({"slow": a, "noisy": noisy})
        self.assertEqual(L["confidence"], "TIE")        # 0.10 gap but within 2 standard errors of run variance


if __name__ == "__main__":
    unittest.main()
