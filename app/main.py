"""FastAPI application: CAPTCHA Solving, Verification & Authorized Contact Form Automation Tool."""
from __future__ import annotations

import base64
import csv
import io
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.automation.browser_handler import automate_contact_form
from app.config import DEFAULT_CSV_PATH, OFFICIAL_TEST_KEYS
from app.solver.detector import detect_from_html, normalize_csv_captcha_label
from app.solver.generator import generate_synthetic_captcha
from app.solver.ocr_solver import solve_image_bytes
from app.solver.providers import get_pricing_table
from app.verification.verifier import verifier_service

app = FastAPI(
    title="CAPTCHA Solving & Verification Tool",
    version="1.0.0",
    description="Recognize, solve, and verify CAPTCHA challenges in authorized test environments.",
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory state for imported contacts, synthetic challenges, and metrics
CONTACT_RECORDS: list[dict] = []
SYNTHETIC_CHALLENGES: dict[str, str] = {}
ATTEMPT_LOGS: list[dict] = []


def _load_csv_bytes(raw_bytes: bytes) -> list[dict]:
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    records = []
    for idx, row in enumerate(reader, start=1):
        det = normalize_csv_captcha_label(row.get("Captcha", "none"))
        records.append({
            "id": idx,
            "company": row.get("Company", "").strip(),
            "website": row.get("Website", "").strip(),
            "city": row.get("City", "").strip(),
            "state": row.get("State", "").strip(),
            "category": row.get("Category", "").strip(),
            "platform": row.get("Platform", "").strip(),
            "captcha_raw": row.get("Captcha", "").strip(),
            "challenge_type": det.challenge_type,
            "provider": det.provider,
            "supported": det.supported,
            "contact_page": row.get("Contact Page", "").strip(),
        })
    return records


def _record_attempt(
    challenge_type: str,
    provider: str,
    method: str,
    success: bool,
    processing_ms: float,
    estimated_cost_usd: float = 0.0,
    detail: str = "",
) -> None:
    ATTEMPT_LOGS.insert(
        0,
        {
            "id": uuid.uuid4().hex[:8],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "challenge_type": challenge_type,
            "provider": provider,
            "method": method,
            "success": success,
            "processing_ms": round(processing_ms, 2),
            "estimated_cost_usd": round(estimated_cost_usd, 6),
            "detail": detail,
        },
    )
    if len(ATTEMPT_LOGS) > 250:
        del ATTEMPT_LOGS[250:]


@app.on_event("startup")
def startup_load_default_csv() -> None:
    global CONTACT_RECORDS
    if DEFAULT_CSV_PATH.exists():
        CONTACT_RECORDS[:] = _load_csv_bytes(DEFAULT_CSV_PATH.read_bytes())


@app.get("/", response_class=HTMLResponse)
def serve_ui() -> HTMLResponse:
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(index_file.read_text(encoding="utf-8"))


@app.get("/api/contacts")
def list_contacts(
    captcha: Optional[str] = None,
    platform: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 200,
) -> dict:
    filtered = CONTACT_RECORDS
    if captcha and captcha != "all":
        filtered = [r for r in filtered if r["captcha_raw"].lower() == captcha.lower()]
    if platform and platform != "all":
        filtered = [r for r in filtered if r["platform"].lower() == platform.lower()]
    if q:
        ql = q.lower()
        filtered = [
            r for r in filtered
            if ql in r["company"].lower() or ql in r["contact_page"].lower() or ql in r["platform"].lower()
        ]

    captcha_counts = Counter(r["captcha_raw"] for r in CONTACT_RECORDS)
    platform_counts = Counter(r["platform"] for r in CONTACT_RECORDS)
    return {
        "total": len(CONTACT_RECORDS),
        "filtered_count": len(filtered),
        "captcha_summary": dict(captcha_counts),
        "platform_summary": dict(platform_counts),
        "records": filtered[:limit],
    }


@app.post("/api/import-csv")
async def import_csv(file: UploadFile = File(...)) -> dict:
    global CONTACT_RECORDS
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")
    CONTACT_RECORDS[:] = _load_csv_bytes(content)
    return {
        "status": "imported",
        "filename": file.filename,
        "total": len(CONTACT_RECORDS),
        "captcha_summary": dict(Counter(r["captcha_raw"] for r in CONTACT_RECORDS)),
    }


class DetectRequest(BaseModel):
    html: str


@app.post("/api/detect")
def detect_challenge(req: DetectRequest) -> dict:
    res = detect_from_html(req.html).to_dict()
    return res


@app.get("/api/generate-synthetic")
def api_generate_synthetic(
    kind: Literal["text", "math"] = "text",
    difficulty: Literal["easy", "medium", "hard"] = "medium",
) -> dict:
    data = generate_synthetic_captcha(kind=kind, difficulty=difficulty)
    cid = uuid.uuid4().hex[:10]
    SYNTHETIC_CHALLENGES[cid] = data["expected_answer"]
    return {
        "challenge_id": cid,
        "kind": data["kind"],
        "difficulty": data["difficulty"],
        "expected_answer": data["expected_answer"],
        "image_base64": data["image_base64"],
        "mime_type": data["mime_type"],
    }


@app.post("/api/solve-image")
async def api_solve_image(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    mode: Literal["auto", "text", "math"] = Form("auto"),
    expected_answer: Optional[str] = Form(None),
) -> dict:
    if file is not None:
        img_bytes = await file.read()
    elif image_base64:
        raw_b64 = image_base64.split(",", 1)[1] if "," in image_base64 else image_base64
        img_bytes = base64.b64decode(raw_b64)
    else:
        raise HTTPException(status_code=400, detail="Provide either an image file or image_base64.")

    res = solve_image_bytes(img_bytes, mode=mode)
    matched = None
    if expected_answer is not None:
        matched = res["solution"].strip().upper() == expected_answer.strip().upper()
        res["ground_truth_match"] = matched

    _record_attempt(
        challenge_type=res.get("challenge_type", "synthetic_text"),
        provider="Custom OpenCV + Tesseract",
        method=res.get("method", "custom_opencv_tesseract"),
        success=bool(res["success"]) and (matched is not False),
        processing_ms=res.get("processing_ms", 0.0),
        estimated_cost_usd=0.0,
        detail=f"Solved '{res.get('solution', '')}' (conf={res.get('confidence', 0)})",
    )
    return res


class IssueTokenRequest(BaseModel):
    provider: str = "recaptcha_v2"
    ttl_seconds: int = 120


@app.post("/api/issue-test-token")
def api_issue_test_token(req: IssueTokenRequest) -> dict:
    token = verifier_service.issue_local_token(req.provider, ttl_seconds=req.ttl_seconds)
    return {"provider": req.provider, "token": token, "ttl_seconds": req.ttl_seconds}


class VerifyTokenRequest(BaseModel):
    provider: str
    token: Optional[str] = None


@app.post("/api/verify-token")
def api_verify_token(req: VerifyTokenRequest, request: Request) -> dict:
    client_ip = request.client.host if request.client else "127.0.0.1"
    res = verifier_service.verify_token(req.provider, req.token, remote_ip=client_ip)
    _record_attempt(
        challenge_type=req.provider,
        provider=req.provider,
        method="server_token_verification",
        success=res["success"],
        processing_ms=res["processing_ms"],
        estimated_cost_usd=0.0,
        detail=res.get("error_code") or "verified",
    )
    return res


class BatchBenchmarkRequest(BaseModel):
    count: int = 10
    kind: Literal["text", "math"] = "text"
    difficulty: Literal["easy", "medium", "hard"] = "medium"


@app.post("/api/batch-benchmark")
def api_batch_benchmark(req: BatchBenchmarkRequest) -> dict:
    count = max(1, min(req.count, 50))
    start = time.perf_counter()
    correct = 0
    results = []
    for i in range(count):
        gen = generate_synthetic_captcha(kind=req.kind, difficulty=req.difficulty, seed=1000 + i)
        img_bytes = base64.b64decode(gen["image_base64"])
        solved = solve_image_bytes(img_bytes, mode=req.kind)
        is_match = solved["solution"].strip().upper() == gen["expected_answer"].strip().upper()
        if is_match:
            correct += 1
        results.append({
            "index": i + 1,
            "expected": gen["expected_answer"],
            "predicted": solved["solution"],
            "match": is_match,
            "confidence": solved["confidence"],
            "processing_ms": solved["processing_ms"],
        })
    total_ms = round((time.perf_counter() - start) * 1000, 2)
    accuracy = round((correct / count) * 100, 1)
    _record_attempt(
        challenge_type=f"synthetic_{req.kind}",
        provider="Custom OpenCV + Tesseract",
        method="batch_benchmark",
        success=accuracy >= 70.0,
        processing_ms=total_ms,
        estimated_cost_usd=0.0,
        detail=f"{correct}/{count} ({accuracy}%)",
    )
    return {
        "count": count,
        "correct": correct,
        "accuracy_pct": accuracy,
        "total_ms": total_ms,
        "avg_ms_per_challenge": round(total_ms / count, 2),
        "samples": results[:15],
    }


@app.get("/api/stats")
def api_stats() -> dict:
    total = len(ATTEMPT_LOGS)
    success_count = sum(1 for a in ATTEMPT_LOGS if a["success"])
    fail_count = total - success_count
    avg_ms = round(sum(a["processing_ms"] for a in ATTEMPT_LOGS) / total, 2) if total else 0.0
    total_cost = round(sum(a["estimated_cost_usd"] for a in ATTEMPT_LOGS), 6)
    return {
        "total_attempts": total,
        "successful_attempts": success_count,
        "failed_attempts": fail_count,
        "success_rate_pct": round((success_count / total) * 100, 1) if total else 0.0,
        "avg_processing_ms": avg_ms,
        "total_estimated_cost_usd": total_cost,
        "recent_attempts": ATTEMPT_LOGS[:30],
    }


@app.get("/api/pricing")
def api_pricing() -> dict:
    return {"pricing": get_pricing_table()}


# ---------------------------------------------------------------------------
# Authorized Local Contact Us Test Harness Forms (for Selenium/Playwright)
# ---------------------------------------------------------------------------
@app.get("/test-forms/{kind}", response_class=HTMLResponse)
def render_test_form(kind: str) -> HTMLResponse:
    kind_norm = kind.lower()
    widget_html = ""
    script_html = ""

    if kind_norm in ("synthetic_text", "synthetic_math"):
        mode = "math" if kind_norm == "synthetic_math" else "text"
        gen = generate_synthetic_captcha(kind=mode, difficulty="medium")
        cid = uuid.uuid4().hex[:10]
        SYNTHETIC_CHALLENGES[cid] = gen["expected_answer"]
        widget_html = f"""
        <div class="captcha-box" data-captcha-type="{kind_norm}">
          <label>Solve the {'Math' if mode == 'math' else 'Text'} CAPTCHA:</label><br/>
          <img id="captcha-image" src="data:image/png;base64,{gen['image_base64']}" alt="CAPTCHA" /><br/>
          <input type="hidden" name="challenge_id" value="{cid}" />
          <input type="text" name="captcha_answer" placeholder="Enter CAPTCHA answer" required />
        </div>
        """
    elif kind_norm == "recaptcha_v2":
        site_key = OFFICIAL_TEST_KEYS["recaptcha_v2"]["site_key"]
        widget_html = f"""
        <div class="g-recaptcha" data-sitekey="{site_key}">Google reCAPTCHA v2 Test Widget</div>
        <input type="hidden" id="captcha_token" name="captcha_token" value="" />
        """
        script_html = f"""
        <script src="https://www.google.com/recaptcha/api.js" async defer></script>
        <script>
          window.issueTestToken = async function() {{
            const r = await fetch('/api/issue-test-token', {{
              method: 'POST', headers: {{'Content-Type': 'application/json'}},
              body: JSON.stringify({{provider: 'recaptcha_v2'}})
            }});
            const d = await r.json();
            document.getElementById('captcha_token').value = d.token;
          }};
        </script>
        """
    elif kind_norm == "recaptcha_invisible":
        site_key = OFFICIAL_TEST_KEYS["recaptcha_v2"]["site_key"]
        widget_html = f"""
        <div class="g-recaptcha" data-sitekey="{site_key}" data-size="invisible">Invisible reCAPTCHA Test Widget</div>
        <input type="hidden" id="captcha_token" name="captcha_token" value="" />
        """
        script_html = """
        <script>
          window.issueTestToken = async function() {
            const r = await fetch('/api/issue-test-token', {
              method: 'POST', headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({provider: 'recaptcha_invisible'})
            });
            const d = await r.json();
            document.getElementById('captcha_token').value = d.token;
          };
        </script>
        """
    elif kind_norm == "hcaptcha":
        site_key = OFFICIAL_TEST_KEYS["hcaptcha"]["site_key"]
        widget_html = f"""
        <div class="h-captcha" data-sitekey="{site_key}">hCaptcha Test Widget</div>
        <input type="hidden" id="captcha_token" name="captcha_token" value="" />
        """
        script_html = """
        <script src="https://js.hcaptcha.com/1/api.js" async defer></script>
        <script>
          window.issueTestToken = async function() {
            const r = await fetch('/api/issue-test-token', {
              method: 'POST', headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({provider: 'hcaptcha'})
            });
            const d = await r.json();
            document.getElementById('captcha_token').value = d.token;
          };
        </script>
        """
    elif kind_norm == "turnstile":
        site_key = OFFICIAL_TEST_KEYS["turnstile"]["site_key_pass"]
        widget_html = f"""
        <div class="cf-turnstile" data-sitekey="{site_key}">Cloudflare Turnstile Test Widget</div>
        <input type="hidden" id="captcha_token" name="captcha_token" value="" />
        """
        script_html = """
        <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
        <script>
          window.issueTestToken = async function() {
            const r = await fetch('/api/issue-test-token', {
              method: 'POST', headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({provider: 'turnstile'})
            });
            const d = await r.json();
            document.getElementById('captcha_token').value = d.token;
          };
        </script>
        """
    elif kind_norm == "unsupported":
        widget_html = """
        <div class="geetest_challenge" data-provider="gt.geetest.com">GeeTest Slider Challenge (Unsupported)</div>
        """

    html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Authorized Contact Us Test Form ({kind_norm})</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 520px; margin: 40px auto; padding: 20px;">
  <h2>Contact Us — Test Harness ({kind_norm})</h2>
  <form method="post" action="/test-forms/{kind_norm}/submit">
    <p><label>Name:<br/><input type="text" name="name" required style="width:100%;padding:8px;" /></label></p>
    <p><label>Email:<br/><input type="email" name="email" required style="width:100%;padding:8px;" /></label></p>
    <p><label>Message:<br/><textarea name="message" required style="width:100%;padding:8px;"></textarea></label></p>
    {widget_html}
    <p><button type="submit" style="padding:10px 18px;margin-top:12px;">Submit Inquiry</button></p>
  </form>
  {script_html}
</body>
</html>"""
    return HTMLResponse(html)


@app.post("/test-forms/{kind}/submit", response_class=HTMLResponse)
async def submit_test_form(
    kind: str,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    challenge_id: Optional[str] = Form(None),
    captcha_answer: Optional[str] = Form(None),
    captcha_token: Optional[str] = Form(None),
) -> HTMLResponse:
    kind_norm = kind.lower()
    if kind_norm == "none":
        return HTMLResponse("<div id='form-result'>Success: Contact form submitted without CAPTCHA.</div>")

    if kind_norm in ("synthetic_text", "synthetic_math"):
        expected = SYNTHETIC_CHALLENGES.pop(challenge_id or "", None)
        if expected and captcha_answer and expected.upper() == captcha_answer.strip().upper():
            return HTMLResponse("<div id='form-result'>Success: Synthetic CAPTCHA verified and form submitted.</div>")
        return HTMLResponse("<div id='form-result'>Failed: Incorrect or expired synthetic CAPTCHA answer.</div>", status_code=400)

    if kind_norm in ("recaptcha_v2", "recaptcha_invisible", "hcaptcha", "turnstile"):
        res = verifier_service.verify_token(kind_norm, captcha_token)
        if res["success"]:
            return HTMLResponse(f"<div id='form-result'>Success: {kind_norm} token verified and form submitted.</div>")
        return HTMLResponse(f"<div id='form-result'>Failed: {res['error_code']} - {res['message']}</div>", status_code=400)

    return HTMLResponse("<div id='form-result'>Failed: Unsupported CAPTCHA type.</div>", status_code=400)


class AutomateFormRequest(BaseModel):
    target_kind: str = "synthetic_text"
    custom_url: Optional[str] = None
    company_name: Optional[str] = None


@app.post("/api/automate-form")
def api_automate_form(req: AutomateFormRequest, request: Request) -> dict:
    base_url = str(request.base_url).rstrip("/")
    form_url = req.custom_url if req.custom_url else f"{base_url}/test-forms/{req.target_kind}"
    res = automate_contact_form(form_url=form_url)
    _record_attempt(
        challenge_type=res.get("challenge_type", req.target_kind),
        provider=res.get("provider", "Selenium Chromium"),
        method=res.get("method", "selenium_chromium"),
        success=bool(res.get("success")),
        processing_ms=res.get("processing_ms", 0.0),
        estimated_cost_usd=res.get("estimated_cost_usd", 0.0),
        detail=req.company_name or req.target_kind,
    )
    return res
