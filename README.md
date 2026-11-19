# CAPTCHA Solving, Verification & Authorized Contact Form Automation Tool

A standalone FastAPI + OpenCV/Tesseract + Selenium application that imports Contact Us form datasets (including the 200-site `USA_Ecommerce_Platforms_200_Contact_Pages.csv`), identifies CAPTCHA challenges, solves synthetic text/math CAPTCHAs locally, verifies official provider test-key tokens, and executes end-to-end headless Chromium browser automation against authorized test forms.

## Architecture Overview

1. **CAPTCHA Recognition Engine (`app/solver/detector.py`)**:
   - Inspects HTML/DOM markers (`g-recaptcha`, `data-size="invisible"`, `h-captcha`, `cf-turnstile`, synthetic image/math inputs) and CSV labels.
   - Distinguishes supported challenges (`synthetic_text`, `synthetic_math`, `recaptcha_v2`, `recaptcha_invisible`, `hcaptcha`, `turnstile`, `none`) from unsupported ones (`GeeTest`, `Arkose FunCaptcha`, `DataDome`).
2. **Custom Solving Engine (`app/solver/ocr_solver.py` + `app/solver/generator.py`)**:
   - Multi-variant OpenCV preprocessing (2x cubic upscaling, median denoise, Otsu + morphological closing + adaptive thresholding) paired with Tesseract 5 (`--psm 7` whitelist) and safe integer math evaluation.
   - Reports predicted answer, confidence score, preprocessing variant, and latency.
3. **Official Token Verification (`app/verification/verifier.py`)**:
   - Supports official test-key verification flows for Google reCAPTCHA, hCaptcha, and Cloudflare Turnstile, plus local HMAC-SHA256 signed tokens.
   - Enforces single-use replay protection, expiration (`exp`), missing/invalid token rejection, and secret-redacted logging (`redact_secret`).
4. **Browser Automation Form Handler (`app/automation/browser_handler.py`)**:
   - Uses headless Chromium via Selenium to open Contact Us forms, detect CAPTCHA widgets in the live DOM, route to the appropriate solver/token handler, fill form fields, submit, and verify server-side acceptance.
   - Includes built-in authorized local Contact Us test forms (`/test-forms/{kind}`) so workflows can be tested safely without bypassing live third-party protections.
5. **Web Dashboard & CSV Importer (`app/main.py`, `app/static/index.html`)**:
   - Pre-loads `USA_Ecommerce_Platforms_200_Contact_Pages.csv` (200 sites) and allows uploading custom CSVs, running OCR benchmarks, testing token edge cases, and launching Selenium simulations.

## Setup & Running Locally

```bash
# 1. Install Python dependencies (and ensure tesseract-ocr + chromium + chromedriver are installed)
pip install -r requirements.txt

# 2. Configure environment variables (optional; safe test defaults are built in)
cp .env.example .env

# 3. Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

## Running Automated Tests

```bash
python3 -m unittest tests/test_suite.py -v
```

## Cost Breakdown (Third-Party vs. Local)

| Method / Provider | Challenge Type | Cost / 1,000 | Per-Challenge | Notes |
| --- | --- | --- | --- | --- |
| Custom OpenCV + Tesseract | Synthetic Text / Math | $0.00 | $0.00000 | Runs locally; zero API cost |
| Official Provider Test Keys | reCAPTCHA / hCaptcha / Turnstile | $0.00 | $0.00000 | Authorized test/sandbox keys |
| 2Captcha (Adapter) | reCAPTCHA v2 / hCaptcha / Turnstile | $2.99 | $0.00299 | Optional; requires `TWOCAPTCHA_API_KEY` |
| CapSolver (Adapter) | reCAPTCHA v2 / hCaptcha / Turnstile | $1.00–$1.20 | $0.00100–$0.00120 | Optional; requires `CAPSOLVER_API_KEY` |
