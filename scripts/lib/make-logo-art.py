#!/usr/bin/env python3
"""Regenerate scripts/lib/netclaw-logo.ans from netclaw.jpg.

Renders the NetClaw hero image as 256-color ANSI half-block art (each
character cell is two vertical pixels drawn with '▀' + fg/bg colors).
The installer TUI cats the .ans file on terminals that support 256 colors.

Usage: python3 scripts/lib/make-logo-art.py [cols] [rows]
Requires: Pillow
"""
import sys
from pathlib import Path

from PIL import Image, ImageEnhance

LIB_DIR = Path(__file__).resolve().parent
REPO = LIB_DIR.parent.parent
COLS = int(sys.argv[1]) if len(sys.argv) > 1 else 76
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 20

CUBE = [0, 95, 135, 175, 215, 255]


def to256(r, g, b):
    """Map an RGB pixel to the nearest xterm-256 color index."""
    ri, gi, bi = (min(range(6), key=lambda i, v=v: abs(CUBE[i] - v)) for v in (r, g, b))
    idx = 16 + 36 * ri + 6 * gi + bi
    rgb = (CUBE[ri], CUBE[gi], CUBE[bi])
    cube_err = (r - rgb[0]) ** 2 + (g - rgb[1]) ** 2 + (b - rgb[2]) ** 2
    g24 = max(0, min(23, round((0.299 * r + 0.587 * g + 0.114 * b - 8) / 10)))
    gv = 8 + 10 * g24
    gray_err = (r - gv) ** 2 + (g - gv) ** 2 + (b - gv) ** 2
    return 232 + g24 if gray_err < cube_err else idx


def main():
    img = Image.open(REPO / "netclaw.jpg").convert("RGB")
    img = img.crop((60, 30, 1024, 559))  # tighten framing on the lobster + cables
    img = ImageEnhance.Color(img).enhance(1.3)
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = img.resize((COLS, ROWS * 2), Image.LANCZOS)

    px = img.load()
    lines = []
    for row in range(ROWS):
        out, last_fg, last_bg = [], None, None
        for x in range(COLS):
            fg = to256(*px[x, row * 2])
            bg = to256(*px[x, row * 2 + 1])
            codes = []
            if fg != last_fg:
                codes.append(f"38;5;{fg}")
                last_fg = fg
            if bg != last_bg:
                codes.append(f"48;5;{bg}")
                last_bg = bg
            out.append(("\033[" + ";".join(codes) + "m" if codes else "") + "▀")
        lines.append("".join(out) + "\033[0m")

    target = LIB_DIR / "netclaw-logo.ans"
    target.write_text("\n".join(lines) + "\n")
    print(f"wrote {target} ({COLS}x{ROWS} cells)")


if __name__ == "__main__":
    main()
