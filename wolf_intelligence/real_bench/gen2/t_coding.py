"""Gen-2 CODING: Indonesian Rupiah amount parser with a precise spec and 40 hidden tests."""
from __future__ import annotations

import json

from .common2 import code_block, governance, result, run_python_tests

PROMPT = r'''You are writing production Python 3.11 for Wolf's finance tooling. Implement exactly one function:

    def parse_idr(text: str) -> int

It parses a human-typed Indonesian Rupiah amount and returns the whole-rupiah integer. Follow this spec EXACTLY;
anything the spec does not allow must raise ValueError (never another exception type, never a guess).

1. Strip leading/trailing whitespace. Matching of letters is case-insensitive.
2. Sign: EITHER one leading "-" OR the whole value wrapped in parentheses "( ... )" means negative.
   The "-" may appear before or after the currency token ("-Rp 5.000" and "Rp -5.000" are both -5000).
   Parentheses together with "-" anywhere -> ValueError. Unbalanced parentheses -> ValueError.
3. Currency token (optional, at most one): "Rp", "Rp." or "IDR", only at the START of the value (inside the
   parentheses if any), optionally followed by any number of spaces. A currency token anywhere else -> ValueError.
4. Magnitude suffix (optional, at most one), after the number, optionally preceded by spaces, nothing may follow it:
   "k", "rb", "ribu" = x1,000 ; "jt", "juta" = x1,000,000 ; "m", "miliar", "milyar" = x1,000,000,000.
5. The number itself must match exactly one of these forms:
   a. plain digits, optionally with a comma decimal part:          5000   5000,75
   b. Indonesian grouping: 1-3 digits then one or more ".ddd" groups, optional comma decimal part:   1.234.567,89
   c. US grouping: 1-3 digits then one or more ",ddd" groups, optional dot decimal part:            1,234,567.89
   d. digits "." 1-2 digits, ONLY when a magnitude suffix is present:  1.5jt   2.25 rb
   AMBIGUITY RULE (overrides a and c): a number containing exactly one comma, no dot, and exactly 3 digits after
   that comma (e.g. "1,500", "Rp 2,500", "1,500rb") is ambiguous -> ValueError.
   A single dot followed by exactly 3 digits with no comma (e.g. "1.234") is form b.
   Any other arrangement of separators (e.g. "12.34.567", "1.2345", "1.5" without a suffix, "1,5,00") -> ValueError.
6. Result = number x multiplier, computed exactly (no binary floating point error), then rounded to an integer
   with ROUND HALF AWAY FROM ZERO, then negated if negative. "-0,5" -> -1. "0,5" -> 1.
7. Empty input, no digits, extra tokens, or a currency token without a number -> ValueError.

Use only the standard library. Output ONE ```python code block containing the function (helpers allowed) and
nothing else: no tests, no explanation, no file or network access.'''

TESTS: list[tuple[str, object]] = [
    ("Rp 5.000", 5000), ("Rp5.000", 5000), ("IDR 1.234.567", 1234567), ("rp. 12.500,50", 12501),
    ("-Rp 7.500", -7500), ("Rp -7.500", -7500), ("(Rp 7.500)", -7500), ("(-Rp 7.500)", "ValueError"),
    ("1,234,567.89", 1234568), ("1,234.5", 1235), ("1.234,5", 1235), ("-1.234,5", -1235),
    ("2,5 jt", 2500000), ("2.5jt", 2500000), ("1,5 juta", 1500000), ("750rb", 750000), ("750 ribu", 750000),
    ("12K", 12000), ("1.2k", 1200), ("3 M", 3000000000), ("1,25 miliar", 1250000000), ("2 milyar", 2000000000),
    ("1,500", "ValueError"), ("Rp 2,500", "ValueError"), ("1.5", "ValueError"), ("12.34.567", "ValueError"),
    ("1.2345", "ValueError"), ("", "ValueError"), ("Rp", "ValueError"), ("5.000 IDR", "ValueError"),
    ("abc", "ValueError"), ("1,2345", 1), ("0,5", 1), ("-0,5", -1), ("1.000.000,499", 1000000),
    ("Rp 1.000.000 jt", 1000000000000), ("  Rp   5.000  ", 5000), ("5 jt rb", "ValueError"),
    ("1,5,00", "ValueError"), ("(5.000", "ValueError"), ("1,500rb", "ValueError"), ("1.234", 1234),
]

HARNESS = r'''
import json as _j
_T = %s
_res = []
for _inp, _exp in _T:
    try:
        _got = parse_idr(_inp)
        _ok = (_exp != "ValueError") and type(_got) is int and _got == _exp
        _res.append([_inp, _ok, repr(_got)[:40]])
    except ValueError:
        _res.append([_inp, _exp == "ValueError", "ValueError"])
    except Exception as _e:
        _res.append([_inp, False, type(_e).__name__])
print("@@RESULT " + _j.dumps(_res))
'''


def grade(text: str) -> dict:
    gov_ok, gov_note = governance(text)
    code = code_block(text)
    if not code or "def parse_idr" not in code:
        return result(0.0, accuracy=0.0, instruction=0.0, gov_ok=gov_ok, gov_note=gov_note,
                      details={"error": "no python block with parse_idr"}, failure_mode="no_code")
    res, err = run_python_tests(code, HARNESS % json.dumps(TESTS))
    if res is None:
        return result(0.0, accuracy=0.0, instruction=0.5, gov_ok=gov_ok, gov_note=gov_note,
                      details={"error": err}, failure_mode="code_error:" + err[:60])
    passed = sum(1 for r in res if r[1])
    acc = passed / len(TESTS)
    stripped = text.strip()
    instr = 1.0 if stripped.startswith("```") and stripped.endswith("```") else 0.8
    failed = [r[0] for r in res if not r[1]]
    return result(acc, accuracy=acc, instruction=instr, gov_ok=gov_ok, gov_note=gov_note,
                  details={"passed": passed, "total": len(TESTS), "failed_inputs": failed},
                  failure_mode=None if acc == 1 else f"failed {len(failed)}/{len(TESTS)} hidden tests")


REFERENCE = r'''```python
import re
from decimal import Decimal, ROUND_HALF_UP

_MULT = {"k": 1000, "rb": 1000, "ribu": 1000, "jt": 10**6, "juta": 10**6, "m": 10**9, "miliar": 10**9, "milyar": 10**9}

def parse_idr(text: str) -> int:
    if not isinstance(text, str):
        raise ValueError("not a string")
    s = text.strip().lower()
    if not s:
        raise ValueError("empty")
    neg = False
    if s.startswith("(") or s.endswith(")"):
        if not (s.startswith("(") and s.endswith(")")):
            raise ValueError("unbalanced")
        s = s[1:-1].strip()
        neg = True
        if "-" in s:
            raise ValueError("paren and minus")
    if s.startswith("-"):
        neg = True; s = s[1:].strip()
    m = re.match(r"^(rp\.?|idr)\s*", s)
    if m:
        s = s[m.end():]
        if s.startswith("-"):
            if neg:
                raise ValueError("double sign")
            neg = True; s = s[1:]
    m = re.fullmatch(r"([0-9.,]+)\s*(k|rb|ribu|jt|juta|m|miliar|milyar)?", s)
    if not m:
        raise ValueError("bad token")
    num, suf = m.group(1), m.group(2)
    if re.fullmatch(r"\d+,\d{3}", num):
        raise ValueError("ambiguous")
    if re.fullmatch(r"\d+(,\d+)?", num):
        val = Decimal(num.replace(",", "."))
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", num):
        val = Decimal(num.replace(".", "").replace(",", "."))
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", num):
        val = Decimal(num.replace(",", ""))
    elif suf and re.fullmatch(r"\d+\.\d{1,2}", num):
        val = Decimal(num)
    else:
        raise ValueError("bad number")
    val *= _MULT[suf] if suf else 1
    out = int(val.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return -out if neg else out
```'''
