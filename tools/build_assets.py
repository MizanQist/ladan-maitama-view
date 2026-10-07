#!/usr/bin/env python3
"""Stage the renders and semi-detached plans from the Maitama View brochure.

Sources come from SRC (a local folder of the brochure's assets) or, when that is
unset or missing, from the brochure's GitHub Pages site. JPEG renders are resized
to 1800 px wide (q82); the plan PNGs are copied as they are.
Run:  [SRC=/path/to/brochure/assets] python3 tools/build_assets.py
"""
import io, os, shutil, urllib.request
from pathlib import Path
from PIL import Image

SRC = Path(os.environ.get("SRC", "")) if os.environ.get("SRC") else None
PAGES = "https://mizanqist.github.io/maitama-view/assets/"
DST = Path(__file__).resolve().parent.parent / "assets"
RENDERS = ["front-day.jpg", "hero-dusk.jpg", "avenue-corner.jpg", "aerial.jpg",
           "hero-terrace.jpg", "row.jpg", "corner.jpg", "avenue.jpg"]
PLANS = ["plan-s-ground.png", "plan-s-first.png", "plan-s-second.png"]
MAX_W = 1800


def fetch(name: str) -> bytes:
    if SRC and (SRC / name).exists():
        return (SRC / name).read_bytes()
    with urllib.request.urlopen(PAGES + name, timeout=90) as r:
        return r.read()


def main():
    DST.mkdir(exist_ok=True)
    for name in RENDERS:
        im = Image.open(io.BytesIO(fetch(name)))
        im.load()
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        im.convert("RGB").save(DST / name, "JPEG", quality=82, optimize=True, progressive=True)
        print(name, im.size, (DST / name).stat().st_size // 1024, "KB")
    for name in PLANS:
        (DST / name).write_bytes(fetch(name))
        print(name, "copied")


if __name__ == "__main__":
    main()
