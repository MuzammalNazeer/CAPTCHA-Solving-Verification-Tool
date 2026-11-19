"""Custom OpenCV + Tesseract OCR solver for synthetic text and math CAPTCHAs."""
from __future__ import annotations

import base64
import os
import re
import shutil
import time
from typing import Literal

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw

from app.solver.generator import ALPHABET, _load_font

# Check if tesseract binary exists in PATH or standard paths
_TESS_PATHS = [
    shutil.which("tesseract"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
]
TESSERACT_AVAILABLE = False
for p in _TESS_PATHS:
    if p and os.path.exists(p):
        pytesseract.pytesseract.tesseract_cmd = p
        TESSERACT_AVAILABLE = True
        break

# Pre-generate glyph templates for custom OpenCV matcher
_CACHED_TEMPLATES: dict[str, np.ndarray] = {}


def _get_templates() -> dict[str, np.ndarray]:
    if _CACHED_TEMPLATES:
        return _CACHED_TEMPLATES
    font = _load_font(38)
    vocab = ALPHABET + "0123456789+-xX*"
    for ch in vocab:
        t_img = Image.new("L", (50, 60), 255)
        t_draw = ImageDraw.Draw(t_img)
        t_draw.text((6, 4), ch, font=font, fill=0)
        arr = np.array(t_img)
        y_idxs, x_idxs = np.where(arr < 128)
        if len(x_idxs) > 0:
            cropped = arr[y_idxs.min():y_idxs.max() + 1, x_idxs.min():x_idxs.max() + 1]
            _CACHED_TEMPLATES[ch] = 255 - cropped
    return _CACHED_TEMPLATES


def _preprocess_variants(img_bgr: np.ndarray) -> list[tuple[str, np.ndarray]]:
    """Generate multiple preprocessed grayscale/binary variants for robust OCR."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    padded = cv2.copyMakeBorder(gray, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255)
    scaled = cv2.resize(padded, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

    blur = cv2.medianBlur(scaled, 3)
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)

    gblur = cv2.GaussianBlur(scaled, (5, 5), 0)
    _, g_otsu = cv2.threshold(gblur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return [("otsu", otsu), ("cleaned", cleaned), ("gaussian_otsu", g_otsu)]


def _evaluate_math(expr: str) -> str | None:
    """Safely evaluate simple integer math expressions like '12+4' or '9*3'."""
    cleaned = expr.replace(" ", "").replace("x", "*").replace("X", "*")
    m = re.search(r"(\d{1,3})([\+\-\*])(\d{1,3})", cleaned)
    if not m:
        return None
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    if op == "+":
        return str(a + b)
    if op == "-":
        return str(a - b)
    if op == "*":
        return str(a * b)
    return None


def _solve_opencv_connected_components(img_bgr: np.ndarray, mode: str) -> tuple[str, float, str, str]:
    """Pure OpenCV character segmentation and shape correlation solver."""
    templates = _get_templates()
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 205, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cleaned)
    blobs = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area >= 15 and (h >= 12 or (h >= 3 and w >= 8)):
            blobs.append((x, y, w, h, area))

    blobs.sort(key=lambda b: b[0])

    merged = []
    for b in blobs:
        if merged and abs(b[0] - merged[-1][0]) < 12:
            prev = merged.pop()
            nx = min(prev[0], b[0])
            ny = min(prev[1], b[1])
            nw = max(prev[0] + prev[2], b[0] + b[2]) - nx
            nh = max(prev[1] + prev[3], b[1] + b[3]) - ny
            merged.append((nx, ny, nw, nh, prev[4] + b[4]))
        else:
            merged.append(b)

    chars = []
    conf_scores = []
    target_vocab = ALPHABET if mode == "text" else "0123456789+-xX*"

    for x, y, w, h, area in merged:
        patch = cleaned[y:y + h, x:x + w]
        best_ch = ""
        best_score = -1.0
        for ch in target_vocab:
            if ch not in templates:
                continue
            tmpl = templates[ch]
            th, tw = tmpl.shape

            h_ratio = min(h, th) / max(h, th)
            w_ratio = min(w, tw) / max(w, tw)
            if h_ratio < 0.35 or w_ratio < 0.25:
                continue

            resized_tmpl = cv2.resize(tmpl, (w, h), interpolation=cv2.INTER_AREA)
            diff = np.mean(np.abs(patch.astype(float) - resized_tmpl.astype(float)))
            sim = 1.0 - (diff / 255.0)
            score = sim * (h_ratio ** 0.5) * (w_ratio ** 0.5)
            if score > best_score:
                best_score = score
                best_ch = ch
        if best_ch:
            chars.append(best_ch)
            conf_scores.append(best_score)

    sol_text = "".join(chars)
    avg_conf = float(np.mean(conf_scores)) if conf_scores else 0.0
    _, enc = cv2.imencode(".png", 255 - cleaned)
    preview_b64 = base64.b64encode(enc.tobytes()).decode("ascii")
    return sol_text, avg_conf, "opencv_contour_matching", preview_b64


def solve_image_bytes(
    image_bytes: bytes,
    mode: Literal["auto", "text", "math"] = "auto",
) -> dict:
    """Solve a synthetic CAPTCHA image and return solution, confidence, and timing."""
    start = time.perf_counter()
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return {
            "success": False,
            "error": "Invalid or unreadable image data",
            "solution": "",
            "confidence": 0.0,
            "processing_ms": round((time.perf_counter() - start) * 1000, 2),
        }

    best_text = ""
    best_conf = 0.0
    best_variant = "opencv_contour_matching"
    best_preview_b64 = ""

    # Attempt Tesseract if installed; otherwise use high-speed OpenCV solver
    if TESSERACT_AVAILABLE:
        try:
            if mode == "math":
                whitelist = "0123456789+-xX"
            elif mode == "text":
                whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            else:
                whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-*"

            variants = _preprocess_variants(img_bgr)
            for name, proc_img in variants:
                pil_img = Image.fromarray(proc_img)
                for psm in (7, 6, 8):
                    config = f"--psm {psm} -c tessedit_char_whitelist={whitelist}"
                    data = pytesseract.image_to_data(
                        pil_img, config=config, output_type=pytesseract.Output.DICT
                    )
                    tokens = []
                    confs = []
                    for txt, conf in zip(data.get("text", []), data.get("conf", [])):
                        txt_clean = re.sub(r"[^A-Z0-9\+\-\*]", "", txt.strip().upper())
                        try:
                            conf_val = float(conf)
                        except (TypeError, ValueError):
                            conf_val = -1.0
                        if txt_clean and conf_val >= 0:
                            tokens.append(txt_clean)
                            confs.append(conf_val)

                    candidate = "".join(tokens)
                    avg_conf = (sum(confs) / len(confs)) if confs else 0.0

                    if not candidate:
                        raw = pytesseract.image_to_string(pil_img, config=config).strip().upper()
                        candidate = re.sub(r"[^A-Z0-9\+\-\*]", "", raw)
                        if candidate:
                            avg_conf = 55.0

                    score = avg_conf + (10.0 if 3 <= len(candidate) <= 8 else 0.0)
                    if candidate and score > best_conf:
                        best_conf = score
                        best_text = candidate
                        best_variant = f"{name}_psm{psm}"
                        _, enc = cv2.imencode(".png", proc_img)
                        best_preview_b64 = base64.b64encode(enc.tobytes()).decode("ascii")
        except Exception:
            best_text = ""

    # Fallback to OpenCV character segmentation & template matcher
    if not best_text:
        best_text, best_conf, best_variant, best_preview_b64 = _solve_opencv_connected_components(img_bgr, mode)

    math_val = _evaluate_math(best_text) if mode in ("auto", "math") else None
    challenge_type = "synthetic_math" if math_val is not None else "synthetic_text"
    final_solution = math_val if math_val is not None else best_text
    norm_conf = round(min(1.0, max(0.0, best_conf)), 3)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    return {
        "success": bool(final_solution),
        "challenge_type": challenge_type,
        "raw_ocr_text": best_text,
        "solution": final_solution,
        "confidence": norm_conf,
        "preprocessing_variant": best_variant,
        "preprocessed_image_base64": best_preview_b64,
        "method": "custom_opencv_engine",
        "estimated_cost_usd": 0.0,
        "processing_ms": elapsed_ms,
    }
