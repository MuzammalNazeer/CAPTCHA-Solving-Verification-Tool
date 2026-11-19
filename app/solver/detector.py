"""CAPTCHA challenge recognition engine for HTML/DOM, URLs, and images."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class DetectionResult:
    challenge_type: str
    provider: str
    supported: bool
    confidence: float
    site_key: Optional[str] = None
    indicators: list[str] = None
    recommended_handler: str = "manual_review"

    def to_dict(self) -> dict:
        data = asdict(self)
        if data["indicators"] is None:
            data["indicators"] = []
        return data


DETECTION_RULES = [
    {
        "challenge_type": "turnstile",
        "provider": "Cloudflare Turnstile",
        "supported": True,
        "recommended_handler": "official_provider_test_or_adapter",
        "patterns": [
            r"challenges\.cloudflare\.com/turnstile",
            r"cf-turnstile",
            r"turnstile\.render",
        ],
    },
    {
        "challenge_type": "hcaptcha",
        "provider": "hCaptcha",
        "supported": True,
        "recommended_handler": "official_provider_test_or_adapter",
        "patterns": [
            r"js\.hcaptcha\.com/1/api\.js",
            r"hcaptcha\.com",
            r"class=[\"'][^\"']*h-captcha",
            r"data-hcaptcha-sitekey",
        ],
    },
    {
        "challenge_type": "recaptcha_invisible",
        "provider": "Google reCAPTCHA (Invisible)",
        "supported": True,
        "recommended_handler": "official_provider_test_or_adapter",
        "patterns": [
            r"data-size=[\"']invisible[\"']",
            r"grecaptcha\.execute",
            r"recaptcha/api\.js\?render=",
            r"invisible\s*recaptcha",
        ],
    },
    {
        "challenge_type": "recaptcha_v2",
        "provider": "Google reCAPTCHA (v2)",
        "supported": True,
        "recommended_handler": "official_provider_test_or_adapter",
        "patterns": [
            r"google\.com/recaptcha/api\.js",
            r"gstatic\.com/recaptcha",
            r"class=[\"'][^\"']*g-recaptcha",
            r"g-recaptcha-response",
        ],
    },
    {
        "challenge_type": "synthetic_math",
        "provider": "Custom Synthetic Math CAPTCHA",
        "supported": True,
        "recommended_handler": "custom_ocr_solver",
        "patterns": [
            r"data-captcha-type=[\"']synthetic_math[\"']",
            r"synthetic-math-captcha",
            r"solve\s+the\s+math\s+captcha",
        ],
    },
    {
        "challenge_type": "synthetic_text",
        "provider": "Custom Synthetic Text CAPTCHA",
        "supported": True,
        "recommended_handler": "custom_ocr_solver",
        "patterns": [
            r"data-captcha-type=[\"']synthetic_text[\"']",
            r"synthetic-text-captcha",
            r"id=[\"']captcha-image[\"']",
            r"name=[\"']captcha_answer[\"']",
        ],
    },
    {
        "challenge_type": "unsupported_geetest",
        "provider": "GeeTest Slider/Behavioral (Unsupported)",
        "supported": False,
        "recommended_handler": "unsupported_escalate",
        "patterns": [
            r"gt\.geetest\.com",
            r"geetest_challenge",
            r"initGeetest",
        ],
    },
    {
        "challenge_type": "unsupported_arkose",
        "provider": "Arkose Labs FunCaptcha (Unsupported)",
        "supported": False,
        "recommended_handler": "unsupported_escalate",
        "patterns": [
            r"arkoselabs\.com",
            r"funcaptcha",
            r"fc-token",
        ],
    },
    {
        "challenge_type": "unsupported_datadome",
        "provider": "DataDome Challenge (Unsupported)",
        "supported": False,
        "recommended_handler": "unsupported_escalate",
        "patterns": [
            r"geo\.captcha-delivery\.com",
            r"datadome",
        ],
    },
]


def extract_site_key(html: str) -> Optional[str]:
    """Extract data-sitekey or render= site key if present in HTML."""
    m = re.search(r"data-sitekey=[\"']([A-Za-z0-9_\-]{10,80})[\"']", html, re.I)
    if m:
        return m.group(1)
    m2 = re.search(r"recaptcha/api\.js\?render=([A-Za-z0-9_\-]{10,80})", html, re.I)
    if m2 and m2.group(1).lower() != "explicit":
        return m2.group(1)
    return None


def detect_from_html(html: str) -> DetectionResult:
    """Identify CAPTCHA challenge type from HTML/DOM content."""
    if not html or not html.strip():
        return DetectionResult(
            challenge_type="none",
            provider="None",
            supported=True,
            confidence=0.95,
            indicators=["empty_html"],
            recommended_handler="direct_submit",
        )

    site_key = extract_site_key(html)
    for rule in DETECTION_RULES:
        matched = []
        for pat in rule["patterns"]:
            if re.search(pat, html, re.I):
                matched.append(pat)
        if matched:
            conf = min(0.99, 0.78 + 0.08 * len(matched))
            return DetectionResult(
                challenge_type=rule["challenge_type"],
                provider=rule["provider"],
                supported=rule["supported"],
                confidence=round(conf, 2),
                site_key=site_key,
                indicators=matched,
                recommended_handler=rule["recommended_handler"],
            )

    # Generic unsupported check if unknown captcha keywords appear
    if re.search(r"captcha|challenge-platform|bot-check", html, re.I):
        return DetectionResult(
            challenge_type="unsupported_unknown",
            provider="Unknown CAPTCHA Provider (Unsupported)",
            supported=False,
            confidence=0.60,
            site_key=site_key,
            indicators=["generic_captcha_keyword"],
            recommended_handler="unsupported_escalate",
        )

    return DetectionResult(
        challenge_type="none",
        provider="None",
        supported=True,
        confidence=0.96,
        indicators=["no_captcha_markers_found"],
        recommended_handler="direct_submit",
    )


def normalize_csv_captcha_label(label: str) -> DetectionResult:
    """Map CSV 'Captcha' column values to standardized DetectionResult."""
    norm = (label or "").strip().lower()
    mapping = {
        "none": DetectionResult("none", "None", True, 1.0, indicators=["csv_label:none"], recommended_handler="direct_submit"),
        "recaptcha": DetectionResult("recaptcha_v2", "Google reCAPTCHA (v2)", True, 1.0, indicators=["csv_label:reCAPTCHA"], recommended_handler="official_provider_test_or_adapter"),
        "invisible recaptcha": DetectionResult("recaptcha_invisible", "Google reCAPTCHA (Invisible)", True, 1.0, indicators=["csv_label:invisible reCAPTCHA"], recommended_handler="official_provider_test_or_adapter"),
        "hcaptcha": DetectionResult("hcaptcha", "hCaptcha", True, 1.0, indicators=["csv_label:hCaptcha"], recommended_handler="official_provider_test_or_adapter"),
        "turnstile": DetectionResult("turnstile", "Cloudflare Turnstile", True, 1.0, indicators=["csv_label:Turnstile"], recommended_handler="official_provider_test_or_adapter"),
    }
    if norm in mapping:
        return mapping[norm]
    return DetectionResult(
        challenge_type="unsupported_unknown",
        provider=f"Unsupported ({label})",
        supported=False,
        confidence=0.5,
        indicators=[f"csv_label:{label}"],
        recommended_handler="unsupported_escalate",
    )
