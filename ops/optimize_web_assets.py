#!/usr/bin/env python3
"""Resize and recompress public art assets for the website."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "public" / "assets" / "art"
CHANNELS = ("aixchem", "aixbio", "aixmath", "aivoices", "engineering")


def crop_to_ratio(image: Image.Image, ratio: float) -> Image.Image:
    width, height = image.size
    current = width / height
    if abs(current - ratio) < 0.01:
        return image
    if current > ratio:
        new_width = int(height * ratio)
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))
    new_height = int(width / ratio)
    top = (height - new_height) // 2
    return image.crop((0, top, width, top + new_height))


def save_pair(image: Image.Image, stem: str, *, jpeg_quality: int, webp_quality: int) -> None:
    rgb = image.convert("RGB")
    rgb.save(ART / f"{stem}.jpg", "JPEG", quality=jpeg_quality, optimize=True, progressive=True)
    rgb.save(ART / f"{stem}.webp", "WEBP", quality=webp_quality, method=6)


def main() -> int:
    hero = Image.open(ART / "hero.jpg")
    save_pair(hero.resize((960, 540), Image.Resampling.LANCZOS), "hero", jpeg_quality=78, webp_quality=72)
    empty = Image.open(ART / "empty.jpg")
    save_pair(empty.resize((320, 320), Image.Resampling.LANCZOS), "empty", jpeg_quality=76, webp_quality=70)
    for name in CHANNELS:
        image = crop_to_ratio(Image.open(ART / f"{name}.jpg"), 16 / 9)
        image = image.resize((640, 360), Image.Resampling.LANCZOS)
        save_pair(image, name, jpeg_quality=78, webp_quality=72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
