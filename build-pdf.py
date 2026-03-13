#!/usr/bin/env python3
"""
build-pdf.py
Generates a beautiful print-quality PDF using WeasyPrint.
Produces catania-guide.pdf — properly typeset with page numbers,
running chapter headers, correct margins, and widows/orphans control.

Usage: python3 build-pdf.py
Output: catania-guide.pdf
"""

import sys
import importlib.util
from pathlib import Path

# ── Reuse the markdown converter and chapter list from build-book.py ─────────

spec = importlib.util.spec_from_file_location("build_book", Path("build-book.py"))
build_book = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_book)

CHAPTERS  = build_book.CHAPTERS
md_to_html = build_book.md_to_html
embed_images = build_book.embed_images

# ── PDF CSS ───────────────────────────────────────────────────────────────────

PDF_CSS = """
/* ── Page setup ──────────────────────────────────────────────── */
@page {
    size: A4;
    margin: 2.8cm 2.5cm 3cm 2.8cm;

    @bottom-center {
        content: counter(page);
        font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
        font-size: 8.5pt;
        color: #999;
    }

    @top-right {
        content: string(chapter-running);
        font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
        font-size: 7.5pt;
        color: #aaa;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
}

/* Title page and cover: no headers/footers */
@page cover-page {
    margin: 0;
    @bottom-center { content: none; }
    @top-right     { content: none; }
}

@page toc-page {
    @top-right { content: none; }
}

/* ── Reset ───────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html, body {
    margin: 0; padding: 0;
}

/* ── Body typography ─────────────────────────────────────────── */
body {
    font-family: Georgia, 'Palatino Linotype', 'Book Antiqua', serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #1a1a1a;
    background: white;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    widows: 3;
    orphans: 3;
}

/* ── Cover ───────────────────────────────────────────────────── */
.cover {
    page: cover-page;
    width: 21cm;
    height: 29.7cm;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: linear-gradient(155deg, #8B3A1A 0%, #1e3d52 100%);
    text-align: center;
    color: white;
    padding: 3cm 2.5cm;
    margin: -2.8cm -2.5cm -3cm -2.8cm; /* bleed to page edge */
    page-break-after: always;
}

.cover h1 {
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 38pt;
    font-weight: 900;
    margin: 0 0 0.3em;
    letter-spacing: -0.02em;
    color: white;
    border: none;
}

.cover .subtitle {
    font-size: 14pt;
    font-style: italic;
    opacity: 0.9;
    margin: 0 0 0.5em;
}

.cover .dates {
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 10pt;
    opacity: 0.75;
    margin-top: 1.2em;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

/* ── TOC ─────────────────────────────────────────────────────── */
.toc {
    page: toc-page;
    page-break-after: always;
    padding: 0;
    border: none;
    border-radius: 0;
    background: white;
    margin-bottom: 0;
}

.toc h2 {
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 10pt;
    color: #8B3A1A;
    margin: 0 0 1.5em;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 0.5pt solid #ccc;
    padding-bottom: 0.5em;
}

.toc ol {
    margin: 0; padding: 0;
    list-style: none;
    counter-reset: toc;
}

.toc li {
    counter-increment: toc;
    margin-bottom: 0.55em;
    display: flex;
    align-items: baseline;
}

.toc li::before {
    content: counter(toc) ".";
    display: inline-block;
    width: 1.6em;
    color: #999;
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 9pt;
    flex-shrink: 0;
}

.toc a {
    color: #1a1a1a;
    text-decoration: none;
    font-size: 10.5pt;
}

/* TOC leader dots + page numbers via CSS target-counter */
/* (WeasyPrint supports this) */
.toc a::after {
    content: leader('.') target-counter(attr(href), page);
    font-size: 9pt;
    color: #999;
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
}

/* ── Chapter structure ───────────────────────────────────────── */
article.chapter {
    page-break-before: always;
}

/* running header string: set by each h1 */
h1.chapter-title {
    string-set: chapter-running content();
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 22pt;
    font-weight: 800;
    color: #8B3A1A;
    border-bottom: 1.5pt solid #ddd;
    padding-bottom: 0.4em;
    margin-top: 0;
    margin-bottom: 1em;
    page-break-after: avoid;
}

/* ── Headings ────────────────────────────────────────────────── */
h2 {
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 13pt;
    color: #1e3d52;
    margin-top: 1.8em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
}

h3 {
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 11pt;
    color: #1a1a1a;
    margin-top: 1.4em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
}

h4, h5, h6 {
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    margin-top: 1em;
    margin-bottom: 0.3em;
    page-break-after: avoid;
}

/* ── Body text ───────────────────────────────────────────────── */
p {
    margin: 0 0 0.75em;
    text-align: justify;
    hyphens: auto;
}

/* ── Blockquotes ─────────────────────────────────────────────── */
blockquote {
    border-left: 3pt solid #8B3A1A;
    margin: 1.2em 0;
    padding: 0.6em 1em;
    background: #faf8f5;
    font-style: italic;
    color: #444;
    page-break-inside: avoid;
}

blockquote p { margin-bottom: 0.3em; }
blockquote p:last-child { margin-bottom: 0; }
blockquote strong { color: #1a1a1a; font-style: normal; }

/* ── Tables ──────────────────────────────────────────────────── */
.table-wrap {
    margin: 1em 0;
    page-break-inside: avoid;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 9.5pt;
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
}

thead {
    background: #8B3A1A;
    color: white;
}

th {
    padding: 0.4em 0.7em;
    text-align: left;
    font-weight: 600;
    font-size: 8.5pt;
}

td {
    padding: 0.35em 0.7em;
    border-bottom: 0.5pt solid #ddd;
    vertical-align: top;
}

tbody tr:nth-child(even) { background: #f9f7f5; }

/* ── Lists ───────────────────────────────────────────────────── */
ul {
    padding-left: 1.3em;
    margin: 0.5em 0;
}

li {
    margin-bottom: 0.3em;
}

/* ── Images ──────────────────────────────────────────────────── */
figure {
    margin: 1.5em 0;
    text-align: center;
    page-break-inside: avoid;
}

img {
    max-width: 88%;
    height: auto;
    display: block;
    margin: 0 auto;
}

img[src*="svg"] {
    max-width: 92%;
}

/* ── Inline elements ─────────────────────────────────────────── */
strong { color: #1a1a1a; }
em { color: #444; }

code {
    font-family: 'Courier New', monospace;
    font-size: 9pt;
    background: #f0ede8;
    padding: 0.1em 0.3em;
    border-radius: 2pt;
}

a {
    color: #1e3d52;
    text-decoration: none;
}

/* Show URLs in print for external links */
a[href^="http"]::after {
    content: " (" attr(href) ")";
    font-size: 7.5pt;
    color: #999;
    word-break: break-all;
}

/* But NOT for TOC links or section anchors */
.toc a::after { content: leader('.') target-counter(attr(href), page); }

/* ── Horizontal rules ────────────────────────────────────────── */
hr {
    border: none;
    border-top: 0.5pt solid #ddd;
    margin: 1.5em 0;
}

/* ── Hide screen-only elements ───────────────────────────────── */
.back-top { display: none; }

/* ── Footer ──────────────────────────────────────────────────── */
.footer {
    display: none;
}
"""

# ── HTML template ─────────────────────────────────────────────────────────────

def build_pdf_html(chapters_html, toc_entries):
    toc_items = []
    for lvl, slug, title in toc_entries:
        if lvl == 1:
            toc_items.append(f'<li><a href="#{slug}">{title}</a></li>')
    toc_html = '\n    '.join(toc_items)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Catania — A Travel Guide for Your Family</title>
<style>
{PDF_CSS}
</style>
</head>
<body>

<div class="cover">
  <h1>Catania</h1>
  <div class="subtitle">A Travel Guide for Your Family</div>
  <div class="dates">14–20 March 2026 · Eastern Sicily</div>
</div>

<nav class="toc">
  <h2>Contents</h2>
  <ol>
    {toc_html}
  </ol>
</nav>

{chapters_html}

</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def _patch_weasyprint_fonts():
    """
    Some system fonts have malformed OS/2 tables or CFF subroutine tables that
    cause fonttools to crash during PDF font subsetting. Patch WeasyPrint's
    font cleaner to silently skip subsetting for any font that errors out —
    the font gets included whole (slightly larger PDF) rather than crashing.
    """
    try:
        import weasyprint.pdf.fonts as wp_fonts
        original_clean = wp_fonts.Font.clean
        def _safe_clean(self, to_unicode, hinting):
            try:
                original_clean(self, to_unicode, hinting)
            except Exception:
                pass  # bad font: include unsubsetted rather than crash
        wp_fonts.Font.clean = _safe_clean
    except Exception:
        pass


def main():
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        print("ERROR: weasyprint not installed.")
        print("Run: pip3 install weasyprint")
        sys.exit(1)

    _patch_weasyprint_fonts()

    all_html = []
    all_toc  = []

    for i, fname in enumerate(CHAPTERS):
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
    page = build_pdf_html(combined, all_toc)

    print("  Embedding images...")
    page = embed_images(page, Path("."))

    tmp_html = Path("_pdf_build.html")
    tmp_html.write_text(page, encoding="utf-8")

    out_pdf = Path("catania-guide.pdf")
    print("  Rendering PDF with WeasyPrint (this takes ~30 seconds)...")

    doc = HTML(filename=str(tmp_html)).render()
    doc.write_pdf(str(out_pdf))

    tmp_html.unlink()

    size_mb = out_pdf.stat().st_size / (1024 * 1024)
    print(f"\n  Done: catania-guide.pdf ({size_mb:.1f} MB)")
    print("  Open with any PDF reader, or share directly.")


if __name__ == "__main__":
    main()
