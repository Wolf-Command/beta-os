"""Gen-2 VISION/DOCUMENT: skewed, noisy restaurant bill image with a struck-through correction, a discount ->
service -> PPN chain, a smudged receipt number (expected null), and a raw payment label."""
from __future__ import annotations

import random
from pathlib import Path

from .common2 import extract_json, governance, json_only, norm, result, to_int, to_num

ITEMS = [("Nasi Campur Ayam", 12, 35_000), ("Es Teh Manis", 12, 8_000), ("Sate Lilit Ikan", 6, 42_000), ("Plecing Kangkung", 4, 18_000)]
STRUCK = ("Sate Lilit Ikan", 4, 42_000)  # crossed-out original line; corrected to qty 6
SUB = sum(q * p for _, q, p in ITEMS)
DISC = SUB * 10 // 100
SVC = (SUB - DISC) * 5 // 100
PPN = round((SUB - DISC + SVC) * 0.11)
TOTAL = SUB - DISC + SVC + PPN
EXP = {"merchant": "Warung Segar Makmur", "date": "2026-10-02", "time": "14:37", "receipt_no": None, "table": "7",
       "subtotal": SUB, "discount": DISC, "service_charge": SVC, "ppn": PPN, "total": TOTAL, "payment_label": "QRIS BCA",
       "cash_tendered": None}


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def make_png(path: str | Path, font_paths: list[str] | None = None) -> str:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    fps = font_paths or ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/System/Library/Fonts/Menlo.ttc",
                         "/System/Library/Fonts/Supplemental/Courier New.ttf"]
    font = big = hand = None
    for fp in fps:
        try:
            font, big, hand = ImageFont.truetype(fp, 24), ImageFont.truetype(fp, 32), ImageFont.truetype(fp, 26)
            break
        except OSError:
            continue
    W, H = 760, 980
    img = Image.new("RGB", (W, H), (246, 243, 236))
    d = ImageDraw.Draw(img)
    y = 30
    def line(t, f=None, x=40, fill=(25, 25, 25)):
        nonlocal y
        d.text((x, y), t, font=f or font, fill=fill)
        y += 38
    line("WARUNG SEGAR MAKMUR", big, 150)
    line("Jl. Raya Senggigi No. 17, Lombok", None, 120)
    line("-" * 46)
    line("Tgl: 02/10/2026   Jam: 14:37   Meja: 7")
    rn_y = y
    line("No : RCP-2026-55813")
    line("-" * 46)
    for name, q, p in ITEMS:
        if name == STRUCK[0]:
            sy = y
            line(f"{name:<18}{STRUCK[1]:>3} x {fmt(STRUCK[2]):>7} {fmt(STRUCK[1] * STRUCK[2]):>9}")
            d.line((36, sy + 14, 720, sy + 12), fill=(20, 20, 20), width=3)
            d.line((36, sy + 20, 720, sy + 18), fill=(20, 20, 20), width=2)
            line(f"  koreksi -> {q} x {fmt(p)} = {fmt(q * p)}", hand, 60, (30, 40, 140))
        else:
            line(f"{name:<18}{q:>3} x {fmt(p):>7} {fmt(q * p):>9}")
    line("-" * 46)
    line(f"{'Subtotal':<28}{fmt(SUB):>16}")
    line(f"{'Diskon Member 10%':<28}{'-' + fmt(DISC):>16}")
    line(f"{'Service 5%':<28}{fmt(SVC):>16}")
    line(f"{'PPN 11%':<28}{fmt(PPN):>16}")
    line("=" * 46)
    d.text((40, y), "TOTAL", font=big, fill=(10, 10, 10))
    d.text((470, y), fmt(TOTAL), font=big, fill=(10, 10, 10))
    y += 44
    line(f"{'Bayar: QRIS BCA':<28}{fmt(TOTAL):>16}")
    line("Terima kasih atas kunjungan Anda")
    # smudge over the receipt number digits
    rng = random.Random(7)
    for _ in range(900):
        cx, cy = 150 + rng.gauss(150, 55), rn_y + 14 + rng.gauss(0, 9)
        r = rng.randint(3, 9)
        g = rng.randint(60, 110)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(g, g - 10, g - 20))
    # paper noise + skew + slight blur
    px = img.load()
    for _ in range(26000):
        x, yy = rng.randrange(W), rng.randrange(H)
        v = rng.randint(150, 235)
        px[x, yy] = (v, v, v)
    img = img.rotate(-2.6, resample=Image.BICUBIC, expand=True, fillcolor=(210, 205, 195)).filter(ImageFilter.GaussianBlur(0.7))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=88) if str(path).lower().endswith((".jpg", ".jpeg")) else img.save(path)
    return str(path)


PROMPT = f"""Read the attached photo of a restaurant bill (file: receipt2.jpg) and extract its fields EXACTLY as printed.
Rules: use the CORRECTED value wherever a line has been struck through and corrected; if a field is illegible or
absent, return null (never guess or reconstruct it); amounts are integer rupiah; dates ISO (the bill uses dd/mm/yyyy);
payment_label is the payment method text exactly as printed after "Bayar:".
Answer with ONLY one JSON object:
{{"merchant": "", "date": "YYYY-MM-DD", "time": "HH:MM", "receipt_no": "or null", "table": "",
 "items": [{{"name": "", "qty": n, "unit_price": n, "line_total": n}}],
 "subtotal": n, "discount": n, "service_charge": n, "ppn": n, "total": n, "payment_label": "", "cash_tendered": "n or null"}}"""


def grade(text: str) -> dict:
    gov_ok, gov_note = governance(text)
    j = extract_json(text)
    if not isinstance(j, dict):
        return result(0.0, accuracy=0.0, instruction=0.0, gov_ok=gov_ok, gov_note=gov_note, details={"error": "no JSON"}, failure_mode="no_json")
    ok = {}
    for k, v in EXP.items():
        g = j.get(k)
        if v is None:
            ok[k] = g is None or norm(g) in {"", "null", "none"}
        elif k == "discount":  # grader 2.1: sign not specified in the brief; printed as "-84.000"
            ok[k] = to_int(g) is not None and abs(to_int(g)) == v
        elif isinstance(v, int):
            ok[k] = to_int(g) == v
        elif k == "merchant":
            ok[k] = norm(g) == norm(v)
        elif k == "payment_label":
            ok[k] = str(g or "").strip() == v
        else:
            ok[k] = norm(g) == norm(v)
    gi = [i for i in (j.get("items") or []) if isinstance(i, dict)]
    item_ok = []
    for name, q, p in ITEMS:
        key = name.split()[0].lower() + " " + name.split()[1].lower()
        m = [i for i in gi if key in norm(i.get("name"))]
        item_ok.append(bool(m) and to_num(m[0].get("qty")) == q and to_int(m[0].get("unit_price")) == p and to_int(m[0].get("line_total")) == q * p)
    ok["items"] = sum(item_ok) / len(ITEMS) * (1.0 if len(gi) == len(ITEMS) else 0.5)
    crit = []
    if not ok["receipt_no"]:
        crit.append("guessed an illegible receipt number")
    sate = [i for i in gi if "sate lilit" in norm(i.get("name"))]
    if any(to_num(i.get("qty")) == STRUCK[1] for i in sate):
        crit.append("used struck-through value")
    q = sum(float(v) for v in ok.values()) / len(ok)
    return result(q, accuracy=q, instruction=1.0 if json_only(text) else 0.7, gov_ok=gov_ok, gov_note=gov_note,
                  details={"fields": ok, "items": item_ok, "semantic_traps_hit": crit},
                  failure_mode=None if q >= 0.999 else ("traps:" + ";".join(crit) if crit else "field_errors"))


def reference() -> str:
    import json
    return json.dumps({**EXP, "items": [{"name": n, "qty": q, "unit_price": p, "line_total": q * p} for n, q, p in ITEMS]})
