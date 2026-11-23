"""Create a local, numbered step-by-step guide from recent captures.

Pure Pillow code: no cloud, no background uploads, no external fonts required.
"""
from __future__ import annotations

from collections.abc import Sequence

from PIL import Image, ImageDraw, ImageFont

MAX_STEPS = 6
MAX_WIDTH = 1100
MAX_HEIGHT = 750
MARGIN = 24
GAP = 18
HEADER = 44


def compose_steps(images: Sequence[Image.Image]) -> Image.Image:
    """Combine 1–6 screenshots in capture order, scaling before composition.

    Large inputs are downscaled to bound output memory and clipboard size.
    """
    if not 1 <= len(images) <= MAX_STEPS:
        raise ValueError(f"Choose between 1 and {MAX_STEPS} screenshots")

    prepared: list[Image.Image] = []
    for original in images:
        if original.width < 1 or original.height < 1:
            raise ValueError("Empty screenshot")
        frame = original.convert("RGB")
        frame.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
        prepared.append(frame)

    width = max(frame.width for frame in prepared) + 2 * MARGIN
    height = 2 * MARGIN + sum(frame.height + HEADER for frame in prepared)
    height += GAP * (len(prepared) - 1)
    result = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(result)
    font = ImageFont.load_default()
    y = MARGIN
    for number, frame in enumerate(prepared, start=1):
        draw.rounded_rectangle(
            (MARGIN, y + 4, MARGIN + 32, y + 36),
            radius=8,
            fill="#176b46",
        )
        draw.text((MARGIN + 12, y + 13), str(number), font=font, fill="white")
        y += HEADER
        result.paste(frame, (MARGIN, y))
        draw.rectangle(
            (MARGIN, y, MARGIN + frame.width - 1, y + frame.height - 1),
            outline="#d1d5db",
            width=1,
        )
        y += frame.height + GAP
    return result
