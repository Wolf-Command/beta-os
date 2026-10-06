"""Gen-2 STRUCTURED EXTRACTION: supplier invoice e-mail thread with quoted older invoice, credit note, locale traps,
and a supplier-stated figure that is wrong."""
from __future__ import annotations

from .common2 import extract_json, governance, json_only, norm, result, to_int, to_num

PROMPT = r'''Extract the CURRENT supplier invoice from this e-mail thread for Wolf accounts payable. Dates are Indonesian
(dd/mm/yyyy). Amounts use "." for thousands and "," for decimals. Quoted older mail (lines starting with ">") may contain
OTHER documents: extract only invoice INV/BS/2026/0311 and its credit note, and list any other document numbers you
ignored. Compute net_payable = invoice total - credit note TOTAL (including its PPN) from the documents themselves. If a
figure stated by the supplier in prose disagrees with your computation, keep your computation, report the supplier's
figure separately and set discrepancy_flag true. Do not contact anyone; extraction only.

---------------------------------------------------------------------
From: AR Bali Seafood <ar@baliseafood.example>
To: ap@wolf.example
Date: Sat, 14 Mar 2026 09:12 +0800
Subject: RE: RE: Invoice INV/BS/2026/0311 - credit note

Dear Wolf team,
Attached credit note CN/BS/2026/0311-A for the 2 kg udang returned (damaged on arrival), Rp 375.000.
So the net payable for INV/BS/2026/0311 is now Rp 7.339.500. Please pay by the due date.

  CREDIT NOTE  CN/BS/2026/0311-A        Date: 13/03/2026
  Ref invoice: INV/BS/2026/0311         Bill to: AMG
  Udang Vaname (return, damaged)   2 kg x 187.500 = 375.000
  DPP 375.000    PPN 11% 41.250    TOTAL CREDIT 416.250

Regards, Wayan - AR

> From: Storekeeper Wolf <store@wolf.example>
> Date: Thu, 12 Mar 2026 16:40 +0800
> We received the 03/03 delivery but 2 kg of the udang was spoiled; returned with your driver on 12/03.
> Please issue a credit note.
>
> > From: AR Bali Seafood <ar@baliseafood.example>
> > Date: Tue, 3 Mar 2026 18:05 +0800
> > Please find invoice below.
> >
> >   INVOICE  INV/BS/2026/0311     Invoice date: 03/03/2026     Terms: Net 14 days from invoice date
> >   Supplier: CV Bali Seafood Utama        Bill to: AMG      Deliver to: GGV main kitchen
> >   Udang Vaname       20 kg    x 187.500  = 3.750.000
> >   Cumi-cumi          15 kg    x  95.000  = 1.425.000
> >   Kakap fillet     12,5 kg    x 142.000  = 1.775.000
> >   Subtotal (DPP)                           6.950.000
> >   PPN 11%                                    764.500
> >   TOTAL                                    7.714.500
> >
> > > Previous month for reference:
> > > INVOICE  INV/BS/2026/0228   Invoice date: 28/02/2026   Bill to: GGV
> > > Udang Vaname 10 kg x 180.000 = 1.800.000   PPN 198.000   TOTAL 1.998.000   (PAID 05/03/2026)
---------------------------------------------------------------------

Answer with ONLY one JSON object:
{"invoice_number": "", "invoice_date": "YYYY-MM-DD", "due_date": "YYYY-MM-DD", "supplier_name": "", "bill_to_entity": "",
 "deliver_to": "", "lines": [{"description": "", "qty": number, "unit": "", "unit_price": n, "line_total": n}],
 "subtotal": n, "ppn": n, "total": n,
 "credit_note": {"number": "", "date": "YYYY-MM-DD", "dpp": n, "ppn": n, "total": n, "reason": ""},
 "net_payable": n, "supplier_stated_net_payable": n, "discrepancy_flag": true/false, "ignored_documents": [""]}'''

EXP = {"invoice_number": "INV/BS/2026/0311", "invoice_date": "2026-03-03", "due_date": "2026-03-17",
       "supplier_name": "CV Bali Seafood Utama", "bill_to_entity": "AMG", "subtotal": 6_950_000, "ppn": 764_500,
       "total": 7_714_500, "net_payable": 7_298_250, "supplier_stated_net_payable": 7_339_500, "discrepancy_flag": True}
LINES = [("udang", 20, 187_500, 3_750_000), ("cumi", 15, 95_000, 1_425_000), ("kakap", 12.5, 142_000, 1_775_000)]
CN = {"number": "CN/BS/2026/0311-A", "date": "2026-03-13", "dpp": 375_000, "ppn": 41_250, "total": 416_250}


def grade(text: str) -> dict:
    gov_ok, gov_note = governance(text)
    j = extract_json(text)
    if not isinstance(j, dict):
        return result(0.0, accuracy=0.0, instruction=0.0, gov_ok=gov_ok, gov_note=gov_note, details={"error": "no JSON"}, failure_mode="no_json")
    ok = {}
    for k, v in EXP.items():
        g = j.get(k)
        if isinstance(v, bool):
            ok[k] = g is v
        elif isinstance(v, int):
            ok[k] = to_int(g) == v
        else:
            ok[k] = norm(g) == norm(v)
    ok["deliver_to"] = "ggv" in norm(j.get("deliver_to"))
    gl = [l for l in (j.get("lines") or []) if isinstance(l, dict)]
    line_ok = []
    for key, q, up, lt in LINES:
        m = [l for l in gl if key in norm(l.get("description"))]
        line_ok.append(bool(m) and to_num(m[0].get("qty")) == q and to_int(m[0].get("unit_price")) == up and to_int(m[0].get("line_total")) == lt)
    ok["lines"] = all(line_ok) and len(gl) == 3
    cn = j.get("credit_note") or {}
    cn_ok = [norm(cn.get("number")) == norm(CN["number"]), norm(cn.get("date")) == CN["date"]] + [to_int(cn.get(k)) == CN[k] for k in ("dpp", "ppn", "total")]
    ok["credit_note"] = sum(cn_ok) / len(cn_ok)
    ign = {norm(x) for x in (j.get("ignored_documents") or [])}
    ok["ignored_documents"] = "inv/bs/2026/0228" in ign and "inv/bs/2026/0311" not in ign
    n = len(ok)
    q = sum(float(v) for v in ok.values()) / n
    # critical semantic traps
    crit = []
    if to_int(j.get("net_payable")) == 7_339_500:
        crit.append("accepted supplier's wrong net payable")
    if norm(j.get("invoice_date")) == "2026-03-03" and norm(j.get("due_date")) not in {"2026-03-17"}:
        crit.append("due date wrong")
    return result(q, accuracy=q, instruction=1.0 if json_only(text) else 0.7, gov_ok=gov_ok, gov_note=gov_note,
                  details={"fields": ok, "line_ok": line_ok, "semantic_traps_hit": crit},
                  failure_mode=None if q >= 0.999 else "field_errors")


REFERENCE = '{"invoice_number":"INV/BS/2026/0311","invoice_date":"2026-03-03","due_date":"2026-03-17","supplier_name":"CV Bali Seafood Utama","bill_to_entity":"AMG","deliver_to":"GGV main kitchen","lines":[{"description":"Udang Vaname","qty":20,"unit":"kg","unit_price":187500,"line_total":3750000},{"description":"Cumi-cumi","qty":15,"unit":"kg","unit_price":95000,"line_total":1425000},{"description":"Kakap fillet","qty":12.5,"unit":"kg","unit_price":142000,"line_total":1775000}],"subtotal":6950000,"ppn":764500,"total":7714500,"credit_note":{"number":"CN/BS/2026/0311-A","date":"2026-03-13","dpp":375000,"ppn":41250,"total":416250,"reason":"2 kg udang damaged"},"net_payable":7298250,"supplier_stated_net_payable":7339500,"discrepancy_flag":true,"ignored_documents":["INV/BS/2026/0228"]}'
