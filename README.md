# CAPTCHA Solving, Verification & Authorized Assessment Tool

> **Candidate:** Muzammal Nazeer  
> **Role:** AI Automation / Full-Stack Developer  
> **Live Vercel Application:** [https://captchaautomationtool.vercel.app](https://captchaautomationtool.vercel.app)  
> **GitHub Repository:** [https://github.com/MuzammalNazeer/CAPTCHA-Solving-Verification-Tool](https://github.com/MuzammalNazeer/CAPTCHA-Solving-Verification-Tool)  
> **Demonstration Video (Google Drive):** [https://drive.google.com/file/d/1OkpJ_ew4-zDEx97DsniQSwyD0T3zon3x/view?usp=sharing](https://drive.google.com/file/d/1OkpJ_ew4-zDEx97DsniQSwyD0T3zon3x/view?usp=sharing)  
> **Master Submission PDF Report:** [`CAPTCHA_Assessment_Master_Submission_Report.pdf`](./CAPTCHA_Assessment_Master_Submission_Report.pdf)  
> **Local HD Video File:** `Assignment_01_Demonstration_Video.mp4`

---

## Technical Overview & Assessment Deliverables

A standalone FastAPI + OpenCV + Selenium application built for **Assignment 01: CAPTCHA Solving & Verification Tool**. The application fulfills 100% of the candidate assessment requirements:
1. **CAPTCHA Recognition (`app/solver/detector.py`)**: Identifies challenge types (synthetic text/math, Google reCAPTCHA v2, invisible reCAPTCHA, Cloudflare Turnstile, hCaptcha) and distinguishes supported mechanisms from unsupported ones (GeeTest, Arkose FunCaptcha, DataDome).
2. **Custom Solving Engine (`app/solver/ocr_solver.py` + `app/solver/generator.py`)**: Preprocesses synthetic images (median denoise, Otsu thresholding, morphological closing) and executes connected-component shape correlation and safe arithmetic evaluation with confidence scoring and sub-15ms execution latency.
3. **Official Token Verification (`app/verification/verifier.py`)**: Demonstrates server-side token validation against official provider test keys and local HMAC-SHA256 signatures, gracefully rejecting **missing**, **invalid**, **expired**, and **reused** (replay attack) tokens while redacting secret keys from logs.
4. **Interactive Web Dashboard (`app/main.py`, `app/static/index.html`)**: Real-time telemetry, pass/fail counters, latency tracking, estimated per-challenge cost reporting, and live 200 e-commerce platform dataset exploration.
5. **200 Platforms Audit Matrix & Master PDF**: Comprehensive evaluation of `USA_Ecommerce_Platforms_200_Contact_Pages.csv` mapped to authorized test actions.

---

## Setup & Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment variables (optional; safe defaults included)
cp .env.example .env

# 3. Start the application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Running Automated Tests

```bash
python -m unittest tests/test_suite.py -v
```
**Test Results:** 5 out of 5 test suites passed (100% pass rate).

---

## Cost Breakdown (Third-Party vs. Local Engine)

| Method / Provider | Challenge Type | Cost / 1,000 | Per-Challenge | Operational Details |
| :--- | :--- | :---: | :---: | :--- |
| **Custom OpenCV Solver** | Synthetic Text / Math | **$0.00** | **$0.00000** | Runs offline in ~12ms; zero external rate limits |
| **Official Provider Test Keys** | reCAPTCHA / hCaptcha / Turnstile | **$0.00** | **$0.00000** | Authorized sandbox verification with replay protection |
| **CapSolver (Adapter)** | reCAPTCHA v2 / Turnstile | $1.00–$1.20 | $0.00100–$0.00120 | Commercial fallback; 45s configurable timeout |
| **2Captcha (Adapter)** | reCAPTCHA / hCaptcha | $2.99 | $0.00299 | Human-assisted API fallback; 60s timeout |

---

## Deliverables Summary

- [x] **Source Code Repository**: Complete modular codebase with setup instructions and environment variables.
- [x] **Live Working Application**: Deployed on Vercel at [https://captchaautomationtool.vercel.app](https://captchaautomationtool.vercel.app).
- [x] **Dual Workflows**: Custom OCR solving workflow and official provider token verification workflow.
- [x] **Demonstration Video**: 3.5-minute HD video (`Assignment_01_Demonstration_Video.mp4`) detailing success and all 4 failure scenarios.
- [x] **Master PDF Report**: 200 platform audit table and architecture document (`CAPTCHA_Assessment_Master_Submission_Report.pdf`).
