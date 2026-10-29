#!/usr/bin/env python3
"""Build non-sensitive PWA assets from the existing school crest.

The app itself always requires the online PHP/MySQL API; the offline fallback
never implies that clock punches can be recorded without server confirmation.
"""
from __future__ import annotations

import base64
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent


def build_icons(out: Path) -> None:
    logo_html = (ROOT / "Logo.html").read_text(encoding="utf-8")
    match = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", logo_html)
    if not match:
        raise RuntimeError("Expected school logo PNG in mysql-ui/Logo.html")
    crest = Image.open(io.BytesIO(base64.b64decode(match.group(1)))).convert("RGBA")

    for size, filename in [(192, "icon-192.png"), (512, "icon-512.png"), (180, "apple-touch-icon.png")]:
        image = Image.new("RGB", (size, size), "#ffffff")
        draw = ImageDraw.Draw(image)
        h = max(4, size // 60)
        for left, right, color in [
            (0, size // 3, "#0753b9"),
            (size // 3, 2 * size // 3, "#fff200"),
            (2 * size // 3, size, "#df1f2f"),
        ]:
            draw.rectangle((left, 0, right, h), fill=color)
        logo = crest.copy()
        logo.thumbnail((int(size * 0.58), int(size * 0.64)), Image.Resampling.LANCZOS)
        x = (size - logo.width) // 2
        y = (size - logo.height) // 2 + h
        image.paste(logo, (x, y), logo)
        image.save(out / filename, format="PNG", optimize=True)


def build_manifest(out: Path) -> None:
    manifest = {
        "id": "./",
        "name": "eKeberadaan — Perakam Waktu Digital",
        "short_name": "eKeberadaan",
        "description": "Sistem perakam waktu digital SMK Bandar Baru Sungai Lalang",
        "lang": "ms",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": "#f4f7fc",
        "theme_color": "#0753b9",
        "icons": [
            {"src": "./icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "./icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    (out / "manifest.webmanifest").write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


def build_offline_page(out: Path) -> None:
    offline = """<!doctype html>
<html lang="ms"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0753b9">
<title>eKeberadaan — Tiada sambungan internet</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;min-height:100dvh;
display:grid;place-items:center;background:#f4f7fc;color:#172033;
font:16px/1.6 -apple-system,BlinkMacSystemFont,Arial,sans-serif;padding:24px}
main{background:white;max-width:420px;border-radius:22px;padding:28px;
box-shadow:0 14px 45px #092a651a;text-align:center;border-top:5px solid #0753b9}
h1{font-size:22px;line-height:1.3}p{color:#526077}
a{display:inline-block;padding:12px 20px;background:#0753b9;color:white;
text-decoration:none;font-weight:700;border-radius:11px}
</style></head><body><main><h1>Tiada sambungan internet</h1>
<p>eKeberadaan memerlukan internet untuk mengesahkan lokasi dan merekod waktu
ke pangkalan data MySQL. Rekod tidak disimpan secara luar talian.</p>
<a href="./">Cuba semula</a></main></body></html>"""
    (out / "offline.html").write_text(offline, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: build_pwa_assets.py OUTPUT_DIRECTORY")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    build_icons(out)
    build_manifest(out)
    build_offline_page(out)
    print("PWA_ASSETS_OK: icons 192/512/180, manifest and honest online-only fallback")


if __name__ == "__main__":
    main()
