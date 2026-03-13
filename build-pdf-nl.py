#!/usr/bin/env python3
"""
build-pdf-nl.py
Generates catania-gids-nl.pdf — the Dutch translation of the Catania travel guide.

Usage: python3 build-pdf-nl.py
Output: catania-gids-nl.pdf
"""

import sys
import importlib.util
from pathlib import Path

# ── Reuse all helpers from build-pdf.py ──────────────────────────────────────

spec = importlib.util.spec_from_file_location("build_pdf", Path("build-pdf.py"))
build_pdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_pdf)

embed_images          = build_pdf.embed_images
_patch_weasyprint_fonts = build_pdf._patch_weasyprint_fonts

# ── Reuse md_to_html from build-book.py ──────────────────────────────────────

spec2 = importlib.util.spec_from_file_location("build_book", Path("build-book.py"))
build_book = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(build_book)

md_to_html = build_book.md_to_html

# ── Dutch chapter list ────────────────────────────────────────────────────────

NL_CHAPTERS = [
    "nl/chapter-01-welkom-op-sicilie.md",
    "nl/chapter-02-catania-stad.md",
    "nl/chapter-03-praktisch-catania.md",
    "nl/chapter-04-weekplanning.md",
    "nl/chapter-05-etna.md",
    "nl/chapter-06-taormina.md",
    "nl/chapter-07-syracuse.md",
    "nl/chapter-08-kust.md",
    "nl/chapter-09-eten.md",
    "nl/chapter-10-familiepraktijkgids.md",
    "nl/chapter-11-snelle-naslag.md",
]

# ── Dutch PDF CSS (same as English, hyphenation language set to Dutch) ────────

NL_CSS = build_pdf.PDF_CSS.replace(
    "hyphens: auto;",
    "hyphens: auto;\n    -webkit-hyphens: auto;\n    lang: nl;",
)

# ── HTML template (Dutch) ─────────────────────────────────────────────────────

def build_nl_pdf_html(chapters_html, toc_entries):
    toc_items = []
    for lvl, slug, title in toc_entries:
        if lvl == 1:
            toc_items.append(f'<li><a href="#{slug}">{title}</a></li>')
    toc_html = "\n    ".join(toc_items)

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<title>Catania — Een Reisgids voor het Gezin</title>
<style>
{NL_CSS}
</style>
</head>
<body>

<div class="cover">
  <h1>Catania</h1>
  <div class="subtitle">Een reisgids voor het hele gezin</div>
  <div class="dates">14–20 maart 2026 · Oost-Sicilië</div>
</div>

<nav class="toc">
  <h2>Inhoud</h2>
  <ol>
    {toc_html}
  </ol>
</nav>

{chapters_html}

</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    try:
        from weasyprint import HTML
    except ImportError:
        print("ERROR: weasyprint not installed.")
        print("Run: pip3 install weasyprint")
        sys.exit(1)

    _patch_weasyprint_fonts()

    all_html = []
    all_toc  = []

    for i, fname in enumerate(NL_CHAPTERS):
        path = Path(fname)
        if not path.exists():
            print(f"  skip: {fname} (not found)")
            continue
        print(f"  {fname}")
        text = path.read_text(encoding="utf-8")
        html, toc = md_to_html(text, chapter_num=i + 1)
        all_html.append(
            f'<article class="chapter" data-chapter="{i+1}">\n{html}\n</article>'
        )
        all_toc.extend(toc)

    combined = "\n\n".join(all_html)
    page = build_nl_pdf_html(combined, all_toc)

    print("  Afbeeldingen insluiten...")
    page = embed_images(page, Path("."))

    tmp_html = Path("_pdf_build_nl.html")
    tmp_html.write_text(page, encoding="utf-8")

    out_pdf = Path("catania-gids-nl.pdf")
    print("  PDF renderen met WeasyPrint (dit duurt ~30 seconden)...")

    doc = HTML(filename=str(tmp_html)).render()
    doc.write_pdf(str(out_pdf))

    tmp_html.unlink()

    size_mb = out_pdf.stat().st_size / (1024 * 1024)
    print(f"\n  Klaar: catania-gids-nl.pdf ({size_mb:.1f} MB)")
    print("  Open met een PDF-viewer of deel direct.")


if __name__ == "__main__":
    main()
