"""Synthetic CAPTCHA image generator for testing and benchmarking."""
from __future__ import annotations

import base64
import io
import random
from typing import Literal

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Exclude ambiguous 0/O, 1/I


def _load_font(size: int = 38) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_synthetic_captcha(
    kind: Literal["text", "math"] = "text",
    length: int = 5,
    difficulty: Literal["easy", "medium", "hard"] = "medium",
    seed: int | None = None,
) -> dict:
    """Generate a synthetic CAPTCHA image and return base64 PNG + ground truth."""
    rng = random.Random(seed)

    if kind == "math":
        a = rng.randint(2, 19)
        b = rng.randint(1, 9)
        op = rng.choice(["+", "-", "*"])
        if op == "-" and b > a:
            a, b = b, a
        prompt_text = f"{a}{op}{b}"
        answer = str(eval(prompt_text))  # safe: controlled integer arithmetic
        display_text = f"{a} {op.replace('*', 'x')} {b}"
    else:
        prompt_text = "".join(rng.choices(ALPHABET, k=length))
        answer = prompt_text
        display_text = prompt_text

    width = max(220, 38 * len(display_text) + 48)
    height = 84
    img = Image.new("RGB", (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(img)
    font = _load_font(38)

    # Background noise dots
    dot_count = {"easy": 35, "medium": 80, "hard": 160}[difficulty]
    for _ in range(dot_count):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        color = (rng.randint(160, 215), rng.randint(160, 215), rng.randint(160, 215))
        draw.point((x, y), fill=color)

    # Draw characters with controlled spacing and slight vertical jitter
    x_cursor = 26
    for ch in display_text:
        if ch == " ":
            x_cursor += 14
            continue
        y_offset = rng.randint(15, 20) if difficulty != "easy" else 17
        ch_color = (rng.randint(15, 50), rng.randint(20, 60), rng.randint(35, 80))
        draw.text((x_cursor, y_offset), ch, font=font, fill=ch_color)
        x_cursor += 36

    # Light interference lines
    line_count = {"easy": 1, "medium": 1, "hard": 3}[difficulty]
    for _ in range(line_count):
        x1, y1 = rng.randint(0, width // 3), rng.randint(10, height - 10)
        x2, y2 = rng.randint(2 * width // 3, width), rng.randint(10, height - 10)
        l_color = (rng.randint(155, 200), rng.randint(155, 200), rng.randint(155, 200))
        draw.line((x1, y1, x2, y2), fill=l_color, width=1)

    if difficulty == "hard":
        img = img.filter(ImageFilter.SMOOTH)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "kind": f"synthetic_{kind}",
        "difficulty": difficulty,
        "display_text": display_text,
        "expected_answer": answer,
        "image_base64": b64,
        "mime_type": "image/png",
    }
