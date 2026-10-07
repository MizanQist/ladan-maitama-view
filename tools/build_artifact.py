#!/usr/bin/env python3
"""Build a self-contained preview of index.html for the claude.ai artifact.

Images are inlined as data URIs (renders at 1100 px q60, plans as 16-colour PNGs),
`src="assets/…"` attributes are rewritten, and `window.__assets` lets the script's
own asset() resolver find the plan and lightbox images. The document wrappers are
stripped because the artifact host supplies its own skeleton.
Run:  python3 tools/build_artifact.py <out.html>
"""
import base64, io, re, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MAX_W, Q = 1100, 60


def data_uri(path: Path) -> str:
    im = Image.open(path)
    buf = io.BytesIO()
    if path.suffix == ".png":
        if im.width > 1400:
            im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
        im = im.convert("RGBA").quantize(16)
        im.save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        im.convert("RGB").save(buf, "JPEG", quality=Q, optimize=True, progressive=True)
        mime = "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()


def main(out: str):
    html = (ROOT / "index.html").read_text()
    assets = {f"assets/{p.name}": data_uri(p) for p in sorted((ROOT / "assets").iterdir()) if p.suffix in (".jpg", ".png")}
    html = re.sub(r'src="(assets/[^"]+)"', lambda m: f'src="{assets[m.group(1)]}"', html)
    html = html.replace('<link rel="icon" href="favicon.svg" type="image/svg+xml">', "")
    html = html.replace('href="sb2-maitama-view.pdf"', 'href="https://mizanqist.github.io/ladan-maitama-view/sb2-maitama-view.pdf"')  # a relative PDF link cannot resolve from the preview
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    body = re.search(r"<body>(.*?)</body>", html, re.S).group(1)
    head = re.sub(r'<meta (charset|name="viewport")[^>]*>', "", head)
    table = "<script>window.__assets=" + str(assets).replace("'", '"') + ";</script>"
    Path(out).write_text(head.strip() + "\n" + table + "\n" + body.strip())
    print(out, Path(out).stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/sb2-preview.html")
