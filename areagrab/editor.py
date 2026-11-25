"""Render screenshot annotations at the original image resolution."""
from dataclasses import dataclass
from math import hypot

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class Mark:
    tool: str
    start: tuple[int, int]
    end: tuple[int, int]
    color: str
    text: str = ""


def render(image: Image.Image, marks: list[Mark]) -> Image.Image:
    result = image.convert("RGB")
    width = max(3, round(max(image.size) / 350))
    for mark in marks:
        draw = ImageDraw.Draw(result, "RGBA")
        x, y = mark.start
        ex, ey = mark.end
        bounds = (min(x, ex), min(y, ey), max(x, ex), max(y, ey))
        if mark.tool == "mask":
            draw.rectangle(bounds, fill="black")
        elif mark.tool == "highlight":
            draw.rectangle(bounds, fill=(255, 223, 38, 95))
        elif mark.tool == "rectangle":
            draw.rectangle(bounds, outline=mark.color, width=width)
        elif mark.tool == "text":
            try:
                font = ImageFont.truetype("segoeui.ttf", max(18, width * 5))
            except OSError:
                font = ImageFont.load_default(size=max(18, width * 5))
            draw.text(mark.start, mark.text, font=font, fill=mark.color,
                      stroke_width=1, stroke_fill="black")
        else:
            draw.line((mark.start, mark.end), fill=mark.color, width=width)
            length = hypot(ex - x, ey - y)
            if mark.tool == "arrow" and length:
                head = min(width * 5, length)
                ux, uy = (ex - x) / length, (ey - y) / length
                bx, by = ex - ux * head, ey - uy * head
                draw.polygon((mark.end, (bx - uy * head / 2, by + ux * head / 2),
                              (bx + uy * head / 2, by - ux * head / 2)), fill=mark.color)
    return result
