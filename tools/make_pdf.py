#!/usr/bin/env python3
"""Print edition of the SB2 dossier: a full-bleed cover plus twelve A4-landscape pages from index.html.

The live page is loaded in headless Chromium with window.__PRINT set, a print
stylesheet is added, and the sheets are re-cut into fixed 297 x 210 mm pages
(all three floor plans rendered statically). Plan PNGs are flattened onto the
panel colour first so the PDF carries no soft masks.
Run:  python3 tools/make_pdf.py [out.pdf]      (default sb2-maitama-view.pdf)
"""
import asyncio, json, sys, tempfile
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
PANEL = (246, 246, 244)  # --bg2, the plan panel
MM = 96 / 25.4

PRINT_CSS = r"""
@page{size:297mm 210mm;margin:0}
html,body{margin:0;padding:0;background:var(--bg)}
body{display:block}
html{scroll-behavior:auto}
.rail,.bar,.lb,.btns,.tabs,.tbtn,.railclose,.docs li.self{display:none!important}
main{margin:0}
.pg{position:relative;width:297mm;height:210mm;padding:12mm 16mm 16mm;overflow:hidden;background:var(--bg);break-after:page;page-break-after:always}
.pg.band{background:var(--bg2)}
.pg:last-child{break-after:auto;page-break-after:auto}
.pg > *{max-width:none}
.pfoot{position:absolute;left:16mm;right:16mm;bottom:7.5mm;display:flex;justify-content:space-between;gap:6mm;font:500 6.8pt/1 var(--fb);letter-spacing:.22em;text-transform:uppercase;color:var(--ink3)}
.shead{margin-bottom:7mm;padding-bottom:3.2mm;gap:5mm}
.shead h2{font-size:8pt}
.shead .sno,.shead .smeta{font-size:6.6pt}
.title{font-size:24pt;margin-bottom:4mm;max-width:none}
.lede{font-size:10.5pt;line-height:1.5;margin-bottom:3.5mm;max-width:none}
.body{font-size:9pt;line-height:1.5;max-width:none;margin-bottom:.9em}
.cap{font-size:7.4pt;margin-top:3mm}
.sched div{font-size:8.2pt;line-height:1.4;padding:2mm 0;gap:4mm;grid-template-columns:30mm 1fr}
.sched dt{font-size:6.2pt;padding-top:1mm}
.two,.two.rev{grid-template-columns:1fr 1fr;gap:12mm}
/* front cover: full-bleed photograph, no running footer */
.pg.front{padding:0}
.pg.front .front{height:100%;min-height:0;padding:14mm 16mm}
.front .ftop,.front .fbot{font-size:7pt}
.front .ftitle{font-size:96pt}
.front .ftitle small{font-size:7.4pt;margin-bottom:6mm}
.front .fby{font-size:12pt;margin-top:5mm}
.front .cue{display:none}
/* welcome */
.pg.cover .stamp{font-size:6.8pt;margin-bottom:12mm}
.pg.cover .hero{grid-template-columns:1fr 1fr;gap:14mm;align-items:center}
.pg.cover .h1{font-size:40pt;margin-bottom:6mm}
.pg.cover .h1 small{font-size:7pt;margin-bottom:6mm}
.pg.cover .lede{font-size:10.5pt}
.pg.cover .figs{margin-top:10mm;padding-top:5mm;gap:6mm}
.pg.cover .figs .n{font-size:22pt}
.pg.cover .figs .n small{font-size:9pt}
.pg.cover .figs .l{font-size:6.4pt;margin-top:2mm}
.pg.cover .hv{aspect-ratio:auto;height:150mm}
/* enclave */
.sitebox{padding:6mm;border-radius:5mm}
.siteplan{aspect-ratio:auto;height:112mm}
.sitecap{font-size:8pt;min-height:0;margin-top:3mm;padding-top:2.5mm}
.sitecap i{font-size:6pt}
.legend{gap:2mm;margin-top:3mm}
.legend li{height:7.5mm;padding:0 3.5mm;font-size:7pt}
.sp-fence{stroke-dashoffset:0!important}
.enc2{margin-top:0}
.frame.aer{aspect-ratio:auto;height:150mm}
/* block */
.elev{padding:7mm;border-radius:5mm}
.ev-screen{fill:rgba(31,34,39,.3)}
.moves{margin-top:0;gap:8mm}
.moves li{font-size:8.6pt;line-height:1.5;padding-top:3mm}
.moves b{font-size:12.5pt;margin-bottom:2mm}
.wide{margin-top:9mm}
.wide .frame{aspect-ratio:auto;height:110mm}
/* plans */
.planwrap{grid-template-columns:1fr 72mm;gap:9mm;align-items:start}
.planbox{padding:7mm;border-radius:5mm}
.plan{margin:0 auto}
.mk{width:5.2mm;height:5.2mm;margin:-2.6mm 0 0 -2.6mm;font-size:6.6pt;box-shadow:0 0 0 .5mm var(--bg2)}
.planfoot{font-size:7.4pt;margin-top:3.5mm}
.pside h3{font-size:16pt}
.pside .rt{font-size:6.6pt}
.pside p{font-size:8.4pt;margin:3mm 0 4mm}
.homes{gap:5mm}
.homes h4{font-size:6.4pt;margin-bottom:1.5mm}
.rl li{font-size:7.8pt;padding:1.6mm 0;grid-template-columns:6mm 1fr}
.rl li i{font-size:6.2pt}
.levels{margin-top:6mm;padding-top:3.5mm;gap:6mm}
.levels .n{font-size:14pt}
.levels .l{font-size:6.4pt;margin-top:1.5mm}
.foot-note{font-size:7.6pt;margin-top:5mm}
/* materials */
.mats{grid-template-columns:repeat(3,1fr);gap:5mm;margin:6mm 0 0}
.mat{border-radius:4mm}
.mat .sw{aspect-ratio:16/7}
.mat .mt{padding:3.5mm 4mm 4mm}
.mat .mt i{font-size:6.2pt;margin-bottom:1.5mm}
.mat .mt b{font-size:10.5pt}
.mat .mt span{font-size:7.6pt}
.spec{gap:7mm 12mm}
.spec h4{font-size:13pt;margin-bottom:2.5mm}
.spec .sched div{font-size:7.8pt;padding:1.7mm 0;grid-template-columns:24mm 1fr}
/* views */
.gal{grid-auto-rows:33mm;gap:3mm}
.gal figure{border-radius:3.5mm}
.gal figcaption{font-size:7pt;padding:8mm 3.5mm 3mm}
/* desk */
.desk{grid-template-columns:1fr 1fr;gap:14mm}
.acts{margin-top:6mm;gap:3mm}
.act{padding:3.5mm 4mm;grid-template-columns:10mm 1fr auto;gap:4mm;border-radius:3.5mm}
.act .ic{width:10mm;height:10mm}
.act .ic svg{width:4.5mm;height:4.5mm}
.act b{font-size:10.5pt}
.act span{font-size:7.8pt}
.act i{font-size:6.2pt}
.desk h4{font-size:13pt;margin-bottom:3mm}
.docs li{font-size:9pt;padding:3.5mm 0}
.docs li span{font-size:7.6pt}
.docs a,.docs em{font-size:6.2pt}
.docs a{padding:2.5mm 3.5mm}
.disc{margin-top:10mm;padding-top:4mm;font-size:7.4pt;max-width:none}
"""

# Re-cuts the sheets into pages: originals are moved, sheet headers are cloned.
PRINT_JS = r"""
(() => {
  const $ = (s, r) => (r || document).querySelector(s);
  const MM = 96 / 25.4, FOOT = 'Block SB2 at Maitama View · Prepared for Mr Dikko Ladan by Mizan Qist Limited · Private';
  const main = $('main'), pages = [];
  const take = (s) => { const n = $(s); if (!n) throw new Error('missing ' + s); return n; };
  const head = {}; ['enclave', 'block', 'plans', 'materials', 'views', 'desk'].forEach(id => { head[id] = take('#' + id + ' .shead'); });
  const H = (id) => head[id].cloneNode(true);
  const page = (cls, nodes) => { const d = document.createElement('section'); d.className = 'pg ' + cls; nodes.forEach(n => d.appendChild(n)); pages.push(d); };
  /* three floors, each a static clone of the explorer sized to a page height */
  const plans = {};
  ['ground', 'first', 'second'].forEach(f => { window.__renderPlan(f); plans[f] = $('.planwrap').cloneNode(true); });
  const sizePlan = (wrap, hmm) => { const plan = $('.plan', wrap), img = $('img', plan); const w = +img.getAttribute('width'), h = +img.getAttribute('height'), px = hmm * MM; plan.style.height = px + 'px'; plan.style.width = (px * w / h) + 'px'; img.style.width = '100%'; img.style.height = '100%'; };
  sizePlan(plans.ground, 110); sizePlan(plans.first, 132); sizePlan(plans.second, 132);
  /* screen-only wording */
  const lede = take('#plans .lede'); lede.textContent = lede.textContent.replace(' Hover a number, or a room in the list.', ' The numbers key to the room lists.');
  const sc = take('#sitecap'); sc.innerHTML = sc.innerHTML.replace(' · hover any building', '');
  const levels = take('#levels'); levels.querySelectorAll('div[data-f]').forEach(d => d.classList.remove('on'));
  page('cover', [take('#welcome .stamp'), take('#welcome .hero')]);
  page('band', [H('enclave'), take('#enclave .two')]);
  page('band', [H('enclave'), take('#enclave .enc2')]);
  page('', [H('block'), take('#block .two')]);
  page('', [H('block'), take('#block .moves'), take('#block .wide')]);
  page('', [H('plans'), take('#plans .title'), take('#plans .lede'), plans.ground, levels]);
  page('', [H('plans'), plans.first]);
  page('', [H('plans'), plans.second, take('#plans .foot-note')]);
  page('band', [H('materials'), take('#materials .title'), take('#materials .lede'), take('#materials .mats')]);
  page('band', [H('materials'), take('#materials .spec')]);
  page('band', [H('views'), take('#views .title'), take('#views .gal')]);
  page('', [H('desk'), take('#desk .desk'), take('#desk .disc')]);
  page('front', [take('#front')]); pages.unshift(pages.pop());
  pages.slice(1).forEach((p, i, rest) => { const f = document.createElement('div'); f.className = 'pfoot'; f.innerHTML = '<span>' + FOOT + '</span><span>' + String(i + 1).padStart(2, '0') + ' / ' + String(rest.length).padStart(2, '0') + '</span>'; p.appendChild(f); });
  main.innerHTML = ''; pages.forEach(p => main.appendChild(p));
  return pages.length;
})()
"""


def flatten_plans(tmp: Path) -> dict:
    out = {}
    for p in sorted((ROOT / "assets").glob("plan-s-*.png")):
        im = Image.open(p).convert("RGBA")
        bg = Image.new("RGB", im.size, PANEL)
        bg.paste(im, mask=im.split()[3])
        f = tmp / p.name
        bg.save(f, "PNG", optimize=True)
        out["assets/" + p.name] = f.as_uri()
    return out


async def main(out: Path):
    tmp = Path(tempfile.mkdtemp(prefix="sb2print-"))
    assets = flatten_plans(tmp)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": round(297 * MM), "height": round(210 * MM)})
        await pg.add_init_script("window.__PRINT=true;window.__assets=" + json.dumps(assets) + ";")
        await pg.goto((ROOT / "index.html").as_uri())
        await pg.add_style_tag(content=PRINT_CSS)
        n = await pg.evaluate(PRINT_JS)
        await pg.emulate_media(media="print")
        await pg.evaluate("document.fonts.ready")
        # lazy images never load off-screen: make every image eager, then wait (bounded) for them
        await pg.evaluate("[...document.images].forEach(i => { i.loading = 'eager'; })")
        await pg.evaluate("Promise.race([new Promise(r => setTimeout(r, 15000)), Promise.all([...document.images].map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; })))])")
        await pg.wait_for_timeout(400)
        await pg.pdf(path=str(out), width="297mm", height="210mm", print_background=True, prefer_css_page_size=True,
                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        await b.close()
    print(out, n, "pages,", out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sb2-maitama-view.pdf"))
