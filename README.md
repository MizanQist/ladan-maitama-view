# SB2 at Maitama View

Private dossier for Mr Dikko Ladan, who has purchased both homes of Block SB2 (the second semi-detached pair) at Maitama View, Plot 758, CAD Zone A05, Maitama, Abuja.

One page, seven sheets: welcome, the enclave (site plan in metres with SB2 highlighted), your block (facts and a schematic front elevation with levels), floor plans (both homes on each floor, numbered markers), materials and specification, views, and the desk. `index.html` carries the markup, styles and interactions; `assets/` holds eight renders at 1800 px and the three semi-detached plan sheets. Fonts load from Google Fonts (Outfit, Manrope); the design system is the Atlantic View one (grey field, off-white panels, timber accent).

## Hosting

Live at https://mizanqist.github.io/ladan-maitama-view/ from the public repo MizanQist/ladan-maitama-view (GitHub Pages, `main` at `/`; `.nojekyll` is included). `robots.txt` and the robots meta keep the page out of search results. The working copy is `~/Developer/ladan-maitama-view`; the iCloud Desktop copy evicts files.

## Editing

- Copy and figures live in `index.html`. The site plan is drawn in metres in `buildSite()` (`LOT`, `HOUSES`, `ISLAND`, `AVENUE`); the block is the `HOUSES` entry with `mine:true`.
- Floor-plan markers are in `ROOMS` (percentages of each plan image, left-hand home then right-hand home); floor summaries in `FLOOR`.
- Contact details are in the desk sheet (`#wa`, the `tel:` and `mailto:` links).
- `tools/build_assets.py` re-stages the images from the Maitama View brochure (a local folder or its GitHub Pages site); `tools/build_artifact.py <out.html>` builds the self-contained claude.ai preview.

## Print edition

`sb2-maitama-view.pdf` is a twelve-page A4 landscape version of the site (cover, enclave x2, block x2, one page per floor plan, materials x2, views, desk), linked from the desk sheet. `python3 tools/make_pdf.py` regenerates it from `index.html` with Playwright: a print stylesheet and a page cutter are injected at build time, the plan PNGs are flattened onto the panel colour, and the explorer is rendered once per floor. Regenerate after editing copy or plans.
