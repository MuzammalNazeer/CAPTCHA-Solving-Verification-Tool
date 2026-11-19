"""Configuration, official provider test keys, and redaction utilities."""
from __future__ import annotations

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
DEFAULT_CSV_PATH = DATA_DIR / "USA_Ecommerce_Platforms_200_Contact_Pages.csv"

# Local HMAC secret for offline/sandbox token verification (never logged)
LOCAL_HMAC_SECRET = os.getenv("CAPTCHA_LOCAL_HMAC_SECRET", "dev-sandbox-hmac-secret-change-in-prod")
TOKEN_TTL_SECONDS = int(os.getenv("CAPTCHA_TOKEN_TTL_SECONDS", "120"))

# Official publicly documented test keys for controlled integration testing
OFFICIAL_TEST_KEYS = {
    "recaptcha_v2": {
        "site_key": os.getenv("RECAPTCHA_SITE_KEY", "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"),
        "secret_key": os.getenv("RECAPTCHA_SECRET_KEY", "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"),
        "verify_url": "https://www.google.com/recaptcha/api/siteverify",
    },
    "hcaptcha": {
        "site_key": os.getenv("HCAPTCHA_SITE_KEY", "10000000-ffff-ffff-ffff-000000000001"),
        "secret_key": os.getenv("HCAPTCHA_SECRET_KEY", "0x0000000000000000000000000000000000000000"),
        "verify_url": "https://api.hcaptcha.com/siteverify",
    },
    "turnstile": {
        "site_key_pass": os.getenv("TURNSTILE_SITE_KEY", "1x00000000000000000000AA"),
        "site_key_fail": "2x00000000000000000000AB",
        "secret_key_pass": os.getenv("TURNSTILE_SECRET_KEY", "1x0000000000000000000000000000000AA"),
        "secret_key_fail": "2x0000000000000000000000000000000AA",
        "verify_url": "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    },
}

# Third-party solver API configuration (optional; disabled by default)
THIRD_PARTY_PROVIDERS = {
    "2captcha": {
        "api_key": os.getenv("TWOCAPTCHA_API_KEY", ""),
        "cost_per_1k_usd": {
            "synthetic_text": 0.50,
            "recaptcha_v2": 2.99,
            "recaptcha_invisible": 2.99,
            "hcaptcha": 2.99,
            "turnstile": 2.99,
        },
        "timeout_seconds": 60,
    },
    "capsolver": {
        "api_key": os.getenv("CAPSOLVER_API_KEY", ""),
        "cost_per_1k_usd": {
            "synthetic_text": 0.40,
            "recaptcha_v2": 1.00,
            "recaptcha_invisible": 1.20,
            "hcaptcha": 1.20,
            "turnstile": 1.20,
        },
        "timeout_seconds": 45,
    },
}

BROWSER_TIMEOUT_SECONDS = int(os.getenv("BROWSER_TIMEOUT_SECONDS", "15"))
ENABLE_LIVE_PROVIDER_CALLS = os.getenv("ENABLE_LIVE_PROVIDER_CALLS", "false").lower() == "true"


def redact_secret(value: str | None) -> str:
    """Return a safely redacted preview of a token or secret key."""
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def sanitize_log_text(text: str) -> str:
    """Scrub known secret keys or bearer-like tokens from log messages."""
    for provider in OFFICIAL_TEST_KEYS.values():
        for k, v in provider.items():
            if "secret" in k and v:
                text = text.replace(v, redact_secret(v))
    text = re.sub(r"(secret|token|api_key)=([A-Za-z0-9_\-\.]{8,})", r"\1=[REDACTED]", text, flags=re.I)
    return text
