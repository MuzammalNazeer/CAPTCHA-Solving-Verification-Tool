"""End-to-end automated test suite for CAPTCHA recognition, OCR, token verification, and Selenium form handling."""
from __future__ import annotations

import base64
import threading
import time
import unittest

import requests
import uvicorn

from app.main import app, startup_load_default_csv, CONTACT_RECORDS
from app.solver.detector import detect_from_html
from app.solver.generator import generate_synthetic_captcha
from app.solver.ocr_solver import solve_image_bytes
from app.verification.verifier import TokenVerificationService


class CaptchaToolTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        startup_load_default_csv()
        cls.port = 8765
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        config = uvicorn.Config(app, host="127.0.0.1", port=cls.port, log_level="warning")
        cls.server = uvicorn.Server(config)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        for _ in range(30):
            try:
                r = requests.get(f"{cls.base_url}/api/stats", timeout=1)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.should_exit = True

    def test_01_csv_imported_200_rows(self) -> None:
        self.assertEqual(len(CONTACT_RECORDS), 200)
        r = requests.get(f"{self.base_url}/api/contacts", timeout=5)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total"], 200)
        self.assertEqual(data["captcha_summary"].get("reCAPTCHA"), 103)
        self.assertEqual(data["captcha_summary"].get("Turnstile"), 15)
        self.assertEqual(data["captcha_summary"].get("hCaptcha"), 6)

    def test_02_html_detection_supported_and_unsupported(self) -> None:
        d_recap = detect_from_html('<div class="g-recaptcha" data-sitekey="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"></div>')
        self.assertEqual(d_recap.challenge_type, "recaptcha_v2")
        self.assertTrue(d_recap.supported)

        d_turn = detect_from_html('<div class="cf-turnstile" data-sitekey="1x00000000000000000000AA"></div>')
        self.assertEqual(d_turn.challenge_type, "turnstile")
        self.assertTrue(d_turn.supported)

        d_gee = detect_from_html('<div class="geetest_challenge" src="https://gt.geetest.com/gt.js"></div>')
        self.assertEqual(d_gee.challenge_type, "unsupported_geetest")
        self.assertFalse(d_gee.supported)

    def test_03_synthetic_ocr_accuracy(self) -> None:
        correct = 0
        total = 8
        for i in range(total):
            gen = generate_synthetic_captcha(kind="text", difficulty="medium", seed=42 + i)
            res = solve_image_bytes(base64.b64decode(gen["image_base64"]), mode="text")
            if res["solution"] == gen["expected_answer"]:
                correct += 1
        self.assertGreaterEqual(correct, 5, f"Expected >=5/8 OCR accuracy, got {correct}/{total}")

        # Math CAPTCHA check
        m_correct = 0
        for i in range(5):
            gen = generate_synthetic_captcha(kind="math", difficulty="easy", seed=100 + i)
            res = solve_image_bytes(base64.b64decode(gen["image_base64"]), mode="math")
            if res["solution"] == gen["expected_answer"]:
                m_correct += 1
        self.assertGreaterEqual(m_correct, 4, f"Expected >=4/5 math OCR accuracy, got {m_correct}/5")

    def test_04_token_verification_edge_cases(self) -> None:
        svc = TokenVerificationService()
        # Missing token
        r_miss = svc.verify_token("recaptcha_v2", "")
        self.assertFalse(r_miss["success"])
        self.assertEqual(r_miss["error_code"], "MISSING_TOKEN")

        # Invalid token
        r_inv = svc.verify_token("hcaptcha", "INVALID_TOKEN")
        self.assertFalse(r_inv["success"])
        self.assertEqual(r_inv["error_code"], "INVALID_TOKEN")

        # Expired token
        expired = svc.issue_local_token("turnstile", ttl_seconds=-10)
        r_exp = svc.verify_token("turnstile", expired)
        self.assertFalse(r_exp["success"])
        self.assertEqual(r_exp["error_code"], "EXPIRED_TOKEN")

        # Valid token + Replay protection
        valid = svc.issue_local_token("recaptcha_v2", ttl_seconds=60)
        r_ok = svc.verify_token("recaptcha_v2", valid)
        self.assertTrue(r_ok["success"])
        r_reuse = svc.verify_token("recaptcha_v2", valid)
        self.assertFalse(r_reuse["success"])
        self.assertEqual(r_reuse["error_code"], "REUSED_TOKEN")

    def test_05_selenium_contact_form_workflows(self) -> None:
        for kind in ("none", "synthetic_math", "recaptcha_v2", "hcaptcha", "turnstile"):
            r = requests.post(
                f"{self.base_url}/api/automate-form",
                json={"target_kind": kind},
                timeout=30,
            )
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertTrue(data["success"], f"Selenium workflow failed for {kind}: {data}")

        # Unsupported challenge should fail gracefully without crashing
        r_unsup = requests.post(
            f"{self.base_url}/api/automate-form",
            json={"target_kind": "unsupported"},
            timeout=30,
        )
        self.assertEqual(r_unsup.status_code, 200)
        self.assertFalse(r_unsup.json()["success"])


if __name__ == "__main__":
    unittest.main()
