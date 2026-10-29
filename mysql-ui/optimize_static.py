#!/usr/bin/env python3
"""Split the MySQL app's generated static HTML into hashed cacheable assets.

Run only AFTER mysql-ui/index.php renders the static Pages HTML.
This changes asset delivery, never PHP/MySQL RPC or user data.
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import re
import sys


def hashed_asset(output_dir: Path, stem: str, suffix: str, data: bytes) -> str:
    digest = hashlib.sha256(data).hexdigest()[:12]
    name = f"{stem}.{digest}.{suffix}"
    path = output_dir / "assets" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"./assets/{name}"


def extract_block(page: str, pattern: str, min_bytes: int, label: str) -> tuple[str, str]:
    matches = [m for m in re.finditer(pattern, page, re.I | re.S)
               if len(m.group(1).encode("utf-8")) > min_bytes]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one large {label} block, got {len(matches)}")
    match = matches[0]
    return page, match.group(0)


def optimize(output_dir: Path) -> None:
    html_path = output_dir / "index.html"
    page = html_path.read_text(encoding="utf-8")
    original_bytes = len(page.encode("utf-8"))

    # The same school crest was inlined in FOUR places: ~440 KB per page.
    inline_logos = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]{1000,})", page)
    if not inline_logos or len(set(inline_logos)) != 1:
        raise RuntimeError("Expected one repeated school crest; refusing unsafe substitution")
    image_bytes = base64.b64decode(inline_logos[0], validate=True)
    if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Embedded school crest is not PNG")
    image_asset = hashed_asset(output_dir, "logo", "png", image_bytes)
    page = page.replace("data:image/png;base64," + inline_logos[0], image_asset)

    page, style = extract_block(page, r"<style>(.*?)</style>", 30000, "style")
    css = re.fullmatch(r"<style>(.*?)</style>", style, re.I | re.S).group(1)
    css_asset = hashed_asset(output_dir, "app", "css", css.encode("utf-8"))
    page = page.replace(style, f'<link rel="stylesheet" href="{css_asset}">', 1)

    # Keep the small PWA registration script inline, but cache the ~125 KB app.
    page, script = extract_block(page, r"<script>(.*?)</script>", 50000, "application script")
    js = re.fullmatch(r"<script>(.*?)</script>", script, re.I | re.S).group(1)
    if "function runServerRaw(" not in js or "ppdkmy.edu.my/ekeberadaansmkbbsul/api.php" not in js:
        raise RuntimeError("Frontend is not the authenticated PHP/MySQL RPC build")
    if "google.script.run" in js or "gas-shim" in js:
        raise RuntimeError("Legacy Google Sheets RPC found in production bundle")
    js_asset = hashed_asset(output_dir, "app", "js", js.encode("utf-8"))
    page = page.replace(script, f'<script defer src="{js_asset}"></script>', 1)

    if "data:image/png;base64," in page or "google.script.run" in page:
        raise RuntimeError("Inline crest or Sheets RPC remained after optimization")
    html_path.write_text(page, encoding="utf-8")

    final_bytes = len(page.encode("utf-8"))
    if final_bytes >= original_bytes // 3:
        raise RuntimeError(f"Static HTML not sufficiently reduced: {original_bytes} to {final_bytes}")
    print(
        f"MYSQL_ASSET_SPLIT_OK HTML={original_bytes}->{final_bytes} bytes "
        f"logo_refs={len(inline_logos)} CSS={css_asset} JS={js_asset} logo={image_asset}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: optimize_static.py OUTPUT_DIRECTORY")
    optimize(Path(sys.argv[1]))
