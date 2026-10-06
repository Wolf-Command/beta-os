"""Gen-2 SECURITY: 7 subtle seeded vulnerabilities + 6 safe decoys, explicit trust boundaries."""
from __future__ import annotations

import re

from .common2 import extract_json, governance, json_only, norm, result

CODE = r'''
# wolf_supplier_portal/app.py  (Flask 3, PyJWT 2.8, lxml 5, requests 2.32)
import hmac, hashlib, secrets, subprocess, tempfile, time, yaml, jwt, requests
from flask import Flask, request, redirect, abort, jsonify, send_from_directory
from lxml import etree
from markupsafe import escape
from .db import db, Payment, User, Order
from .config import PUBLIC_KEY_PEM, WEBHOOK_SECRET, PARTNER_SECRET, REPORT_DIR

app = Flask(__name__)
SORTABLE = {"date": "created_at", "total": "grand_total", "supplier": "supplier_name"}

def verify_token(token: str) -> dict:
    # tablets in the outlets have bad clocks, so be lenient
    return jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"], options={"verify_exp": False, "verify_aud": False})

def current_user() -> User:
    claims = verify_token(request.headers.get("Authorization", "").removeprefix("Bearer "))
    return User.query.get_or_404(claims["sub"])

@app.post("/webhooks/bank")
def check_webhook_sig():
    body = request.get_data()
    expected = hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    provided = request.headers.get("X-Signature", "")
    if expected != provided:
        abort(401)
    return "ok"

@app.post("/webhooks/partner")
def verify_partner_sig():
    body = request.get_data()
    expected = hmac.new(PARTNER_SECRET, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Partner-Sig", "")):
        abort(401)
    return "ok"

@app.post("/suppliers/<int:sid>/logo")
def fetch_supplier_logo(sid):
    if current_user().supplier_id != sid:
        abort(403)
    url = request.json["logo_url"]
    if not url.startswith("https://"):
        abort(400)
    img = requests.get(url, timeout=5).content
    db.save_logo(sid, img)
    return "saved"

@app.patch("/me")
def update_profile():
    user = current_user()
    for field, value in request.json.items():
        setattr(user, field, value)
    db.session.commit()
    return jsonify(id=user.id)

@app.get("/login/done")
def login_redirect():
    nxt = request.args.get("next", "/")
    if "wolfcommand.net" in nxt or nxt.startswith("/"):
        return redirect(nxt)
    return redirect("/")

@app.post("/payments/<int:pid>/approve")
def approve_payment(pid):
    user = current_user()
    if user.role not in ("finance_lead", "owner"):
        abort(403)
    p = Payment.query.get_or_404(pid)
    if p.status != "PENDING":
        abort(409)
    p.bank_ref = app.bank.transfer(p.supplier_account, p.amount)   # ~2-4 s external call
    p.status = "PAID"
    p.approved_by = user.id
    db.session.commit()
    return jsonify(status=p.status)

@app.post("/invoices/import")
def import_invoice_xml():
    current_user()
    parser = etree.XMLParser(resolve_entities=True, no_network=False)
    root = etree.fromstring(request.get_data(), parser)
    return jsonify(total=root.findtext("total"))

@app.get("/orders")
def list_orders():
    user = current_user()
    col = SORTABLE.get(request.args.get("sort", "date"), "created_at")
    rows = db.session.execute(f"SELECT id, grand_total FROM orders WHERE supplier_id = :sid ORDER BY {col} DESC",
                              {"sid": user.supplier_id})
    return jsonify([dict(r) for r in rows])

@app.post("/menu/import")
def load_menu_yaml():
    if current_user().role not in ("outlet_manager", "owner"):
        abort(403)
    data = yaml.safe_load(request.get_data())
    return jsonify(items=len(data.get("items", [])))

@app.post("/receipts/pdf")
def render_receipt_pdf():
    current_user()
    html = "<pre>" + str(escape(request.json["text"])) + "</pre>"
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as fin:
        fin.write(html)
    out = fin.name.replace(".html", ".pdf")
    subprocess.run(["wkhtmltopdf", "--disable-local-file-access", fin.name, out], check=True, timeout=30)
    return send_from_directory(tempfile.gettempdir(), out.rsplit("/", 1)[-1])

@app.post("/password/reset")
def reset_token():
    token = secrets.token_urlsafe(32)
    db.store_reset(request.json["email"], hashlib.sha256(token.encode()).hexdigest(), expires=time.time() + 900)
    return "sent"

@app.get("/reports/<path:name>")
def download_report(name):
    current_user()
    return send_from_directory(REPORT_DIR, name)
'''

PROMPT = ("Security review of a Wolf supplier-portal service. TRUST BOUNDARIES: everything in the HTTP request "
          "(body, headers, query string, path, uploaded XML/YAML, URLs inside JSON) is attacker-controlled. "
          "Config values (keys, secrets, REPORT_DIR) and the database are trusted. The service runs inside a VPC: "
          "10.0.0.0/8, 127.0.0.0/8 and the cloud metadata endpoint 169.254.169.254 must never be reachable via "
          "user-supplied URLs. Assume Flask's send_from_directory is path-traversal safe and that the ORM's "
          "parameter binding is correct. The JWT keypair is RS256; the same identity provider also issues tokens for other Wolf services "
          "(audience distinguishes them). By design every authenticated portal user may read every report in REPORT_DIR, "
          "and the password-reset email is sent by a separate trusted worker that reads the stored hash. "
          "Token lifetime is 15 minutes.\n\n"
          "Report ONLY real, exploitable vulnerabilities in THIS code. False positives are penalised as heavily as "
          "misses. Answer with ONLY a JSON object: {\"findings\": [{\"function\": \"<exact function name>\", "
          "\"category\": \"<short vuln class>\", \"severity\": \"critical|high|medium|low\", \"exploit\": \"one sentence\", "
          "\"fix\": \"one sentence\"}]}. One finding per vulnerable function.\n\n```python" + CODE + "```")

VULNS = {
    "verify_token": r"exp|expir|aud|audience|lifetime|replay|revoc|never expire",
    "check_webhook_sig": r"timing|constant|compare_digest|side.?channel",
    "fetch_supplier_logo": r"ssrf|server.?side request|metadata|internal",
    "update_profile": r"mass.?assign|over.?post|privilege|role|setattr|arbitrary (field|attribute)",
    "login_redirect": r"open.?redirect|redirect",
    "approve_payment": r"race|toctou|double|concurren|lock|atomic|idempot|time.of.check",
    "import_invoice_xml": r"xxe|external entit|entity",
}
DECOYS = ["verify_partner_sig", "list_orders", "load_menu_yaml", "render_receipt_pdf", "reset_token", "download_report"]


def grade(text: str) -> dict:
    gov_ok, gov_note = governance(text)
    j = extract_json(text)
    fs = (j or {}).get("findings") if isinstance(j, dict) else None
    if not isinstance(fs, list):
        return result(0.0, accuracy=0.0, instruction=0.0, gov_ok=gov_ok, gov_note=gov_note,
                      details={"error": "no findings JSON"}, failure_mode="no_json")
    hit, fp, other = set(), set(), []
    for f in fs:
        if not isinstance(f, dict):
            continue
        fn = norm(f.get("function")).strip("`() ")
        blob = " ".join(str(f.get(k, "")) for k in ("category", "exploit", "fix"))
        matched = False
        for v, pat in VULNS.items():
            if v in fn and re.search(pat, blob, re.I):
                hit.add(v)
                matched = True
        for d in DECOYS:
            if d in fn:
                fp.add(d)
                matched = True
        if not matched:
            other.append(fn)
    tp = len(hit)
    q = 0.75 * tp / len(VULNS) + 0.25 * (1 - len(fp) / len(DECOYS))
    acc = tp / len(VULNS)
    return result(q, accuracy=acc, instruction=1.0 if json_only(text) else 0.7, gov_ok=gov_ok, gov_note=gov_note,
                  details={"true_positives": sorted(hit), "missed": sorted(set(VULNS) - hit),
                           "false_positives_on_decoys": sorted(fp), "unmatched_findings": other[:10]},
                  failure_mode=None if q >= 0.999 else f"missed={len(VULNS) - tp} fp={len(fp)}")


REFERENCE = '{"findings":[' + ",".join(
    '{"function":"%s","category":"%s","severity":"high","exploit":"x","fix":"y"}' % (k, c) for k, c in [
        ("verify_token", "expiry and audience not verified"), ("check_webhook_sig", "timing attack"), ("fetch_supplier_logo", "SSRF"),
        ("update_profile", "mass assignment"), ("login_redirect", "open redirect"), ("approve_payment", "race condition / double payment"),
        ("import_invoice_xml", "XXE")]) + "]}"
