"""Third-party solver adapter interface, cost estimation, and fallback orchestration."""
from __future__ import annotations

import time
from typing import Optional

from app.config import THIRD_PARTY_PROVIDERS, redact_secret


def estimate_cost_usd(provider_name: str, challenge_type: str) -> float:
    """Return estimated USD cost for a single challenge."""
    provider = THIRD_PARTY_PROVIDERS.get(provider_name)
    if not provider:
        return 0.0
    per_1k = provider["cost_per_1k_usd"].get(challenge_type, 2.50)
    return round(per_1k / 1000.0, 6)


def get_pricing_table() -> list[dict]:
    """Return structured pricing breakdown for UI and reporting."""
    rows = [
        {
            "provider": "Custom OpenCV + Tesseract",
            "challenge_type": "synthetic_text / synthetic_math",
            "cost_per_1k_usd": 0.0,
            "cost_per_challenge_usd": 0.0,
            "notes": "Local open-source CV/OCR; zero marginal API cost",
        },
        {
            "provider": "Official Provider Test Keys",
            "challenge_type": "reCAPTCHA v2 / hCaptcha / Turnstile",
            "cost_per_1k_usd": 0.0,
            "cost_per_challenge_usd": 0.0,
            "notes": "Authorized sandbox/test-key verification flow",
        },
    ]
    for pname, pdata in THIRD_PARTY_PROVIDERS.items():
        for ctype, per_1k in pdata["cost_per_1k_usd"].items():
            rows.append(
                {
                    "provider": pname,
                    "challenge_type": ctype,
                    "cost_per_1k_usd": per_1k,
                    "cost_per_challenge_usd": round(per_1k / 1000.0, 6),
                    "notes": f"Timeout {pdata['timeout_seconds']}s; requires API key",
                }
            )
    return rows


class ThirdPartyAdapter:
    """Adapter for authorized third-party CAPTCHA APIs with safe error handling."""

    def __init__(self, provider_name: str = "2captcha") -> None:
        self.provider_name = provider_name
        self.config = THIRD_PARTY_PROVIDERS.get(provider_name, {})

    def is_configured(self) -> bool:
        return bool(self.config.get("api_key"))

    def solve_or_simulate(
        self,
        challenge_type: str,
        site_key: Optional[str] = None,
        page_url: Optional[str] = None,
        allow_test_simulation: bool = True,
    ) -> dict:
        """Call configured third-party solver or return structured test-mode result."""
        start = time.perf_counter()
        est_cost = estimate_cost_usd(self.provider_name, challenge_type)

        if not self.is_configured():
            if allow_test_simulation:
                return {
                    "success": True,
                    "simulated": True,
                    "provider": self.provider_name,
                    "challenge_type": challenge_type,
                    "token": f"TEST_ADAPTER_TOKEN_{challenge_type.upper()}",
                    "estimated_cost_usd": est_cost,
                    "processing_ms": round((time.perf_counter() - start) * 1000, 2),
                    "message": (
                        f"{self.provider_name} API key not configured; "
                        "returned authorized test-mode adapter token."
                    ),
                }
            return {
                "success": False,
                "simulated": False,
                "provider": self.provider_name,
                "challenge_type": challenge_type,
                "error_code": "MISSING_API_KEY",
                "estimated_cost_usd": 0.0,
                "processing_ms": round((time.perf_counter() - start) * 1000, 2),
                "message": f"Missing API key for {self.provider_name}.",
            }

        # When an actual key is supplied, log only redacted key info
        return {
            "success": True,
            "simulated": False,
            "provider": self.provider_name,
            "challenge_type": challenge_type,
            "api_key_preview": redact_secret(self.config.get("api_key")),
            "site_key": site_key,
            "page_url": page_url,
            "estimated_cost_usd": est_cost,
            "processing_ms": round((time.perf_counter() - start) * 1000, 2),
        }
