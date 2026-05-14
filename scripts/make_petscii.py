#!/usr/bin/env python3
"""
make_petscii.py
================
Converts a marine larval-dispersal map (or any 2D image) into two outputs:

  1. A PETSCII-style text mosaic (Commodore PET / C64 aesthetic).
  2. A pixel-art SVG mosaic with a fixed 16-colour palette evocative
     of the Amiga 1200 default palette.

Usage:
  python scripts/make_petscii.py <input_image> \
      [--cols 80] [--out-text easter-egg.txt] [--out-svg easter-egg.svg]

Why two formats:
  - The text mosaic embeds beautifully inside a fenced code block in the
    README; it costs zero KB and renders identically everywhere.
  - The SVG mosaic gives a true Amiga-pixel feel and scales cleanly.

Dependencies:
  - Pillow only. (pip install pillow)
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.stderr.write(
        "[error] Pillow is required: pip install pillow\n"
    )
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────────────────
# PETSCII-ish ramp — dark → light
# Chosen for grayscale rendering of dispersal density maps.
# ──────────────────────────────────────────────────────────────────────────────
PETSCII_RAMP = " .,:;+=*#%@█"  # 12 levels, dark → light

# Amiga-ish 16-colour palette (RGB).
# Approximates the default Workbench 1.3/2.0 mix plus oceanic accents.
AMIGA_PALETTE = [
    (0x00, 0x00, 0x00),  # 0  black
    (0x0a, 0x1a, 0x4a),  # 1  deep navy
    (0x18, 0x36, 0x7a),  # 2  ocean blue
    (0x2c, 0x5a, 0xa8),  # 3  mid blue
    (0x4a, 0x88, 0xc8),  # 4  light blue
    (0x6e, 0xb1, 0xd4),  # 5  surf
    (0x9a, 0xd2, 0xe6),  # 6  pale teal
    (0xc4, 0xe8, 0xee),  # 7  almost-white teal
    (0xee, 0xee, 0xd0),  # 8  sand
    (0xd4, 0xb0, 0x70),  # 9  beach
    (0xa0, 0x70, 0x30),  # 10 driftwood
    (0x70, 0x40, 0x18),  # 11 deep brown
    (0xc8, 0x40, 0x40),  # 12 coral red
    (0xee, 0x88, 0x40),  # 13 amber
    (0xff, 0xb0, 0x00),  # 14 retro orange
    (0xff, 0xff, 0xff),  # 15 white
]

def _nearest_palette_index(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    best, best_d = 0, 10**9
    for i, (pr, pg, pb) in enumerate(AMIGA_PALETTE):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_d:
            best, best_d = i, d
    return best


def to_petscii(img: Image.Image, cols: int) -> str:
    """Reduces the image to a text mosaic using PETSCII_RAMP."""
    w, h = img.size
    # Characters are roughly 2:1 (height:width) → halve the row count.
    rows = max(1, int(cols * h / w / 2))
    small = img.convert("L").resize((cols, rows), Image.Resampling.LANCZOS)
    pix = small.load()
    n = len(PETSCII_RAMP) - 1
    out_rows = []
    for y in range(rows):
        line = "".join(PETSCII_RAMP[int(pix[x, y] / 255 * n)] for x in range(cols))
        out_rows.append(line)
    return "\n".join(out_rows)


def to_amiga_svg(img: Image.Image, cols: int) -> str:
    """Reduces the image to a pixel-art SVG using the 16-colour Amiga-ish palette."""
    w, h = img.size
    rows = max(1, int(cols * h / w))
    small = img.convert("RGB").resize((cols, rows), Image.Resampling.LANCZOS)
    pix = small.load()
    cell = 8  # pixels per "Amiga pixel"
    svg_w = cols * cell
    svg_h = rows * cell

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}"',
        '     shape-rendering="crispEdges" role="img"',
        '     aria-label="Larval dispersal — Amiga-style pixel art mosaic">',
        '  <rect width="100%" height="100%" fill="#000"/>',
    ]
    # Group by palette index to keep the SVG small.
    buckets: dict[int, list[tuple[int, int]]] = {}
    for y in range(rows):
        for x in range(cols):
            idx = _nearest_palette_index(pix[x, y])
            buckets.setdefault(idx, []).append((x, y))

    for idx, cells in buckets.items():
        r, g, b = AMIGA_PALETTE[idx]
        colour = f"#{r:02x}{g:02x}{b:02x}"
        # Emit one <path> per colour, made of M h moves — very compact.
        d = []
        for x, y in cells:
            d.append(f"M{x*cell} {y*cell}h{cell}v{cell}h-{cell}z")
        parts.append(f'  <path fill="{colour}" d="{"".join(d)}"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="Source image (PNG, JPG, ...)")
    ap.add_argument("--cols", type=int, default=80,
                    help="Width in characters / cells (default: 80)")
    ap.add_argument("--out-text", default="assets/easter-egg/dispersal-petscii.txt",
                    help="Output path for the PETSCII text mosaic")
    ap.add_argument("--out-svg", default="assets/easter-egg/dispersal-amiga.svg",
                    help="Output path for the Amiga-palette pixel-art SVG")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        sys.stderr.write(f"[error] file not found: {src}\n")
        return 1

    img = Image.open(src)

    text_mosaic = to_petscii(img, args.cols)
    Path(args.out_text).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_text).write_text(text_mosaic, encoding="utf-8")
    print(f"[ok] wrote {args.out_text}")

    svg_mosaic = to_amiga_svg(img, args.cols)
    Path(args.out_svg).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_svg).write_text(svg_mosaic, encoding="utf-8")
    print(f"[ok] wrote {args.out_svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
