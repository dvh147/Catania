#!/usr/bin/env python3
"""
build-book.py
Combines all chapters into a single beautiful HTML page.
Responsive (desktop + phone), print-friendly, self-contained CSS.

Usage: python3 build-book.py
Output: index.html
"""

import base64
import mimetypes
import re
import sys
from pathlib import Path

CHAPTERS = [
    "chapter-01-welcome-to-sicily.md",
    "chapter-02-catania-city.md",
    "chapter-03-practical-catania.md",
    "chapter-04-sample-week.md",
    "chapter-05-etna.md",
    "chapter-06-taormina.md",
    "chapter-07-syracuse.md",
    "chapter-08-coast.md",
    "chapter-09-food.md",
    "chapter-10-family-field-guide.md",
    "chapter-11-quick-reference.md",
]

# ── Markdown → HTML ─────────────────────────────────────────────────────────

def inline(text):
    """Convert inline markdown to HTML."""
    # Images (before links — same bracket syntax)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" loading="lazy">', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    # Bold + italic
    text = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # Bold
    text = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', text)
    # Italic (but not the star ratings ★)
    text = re.sub(r'(?<![★☆])\*([^*\n]+?)\*(?![★☆])', r'<em>\1</em>', text)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text


def md_to_html(text, chapter_num=0):
    """Convert a markdown chapter to HTML."""
    lines = text.split('\n')
    out = []
    state = None   # None | 'bq' | 'table' | 'ul' | 'thead'
    pbuf = []
    toc_entries = []

    def flush_p():
        if pbuf:
            joined = '<br>\n'.join(inline(l) for l in pbuf)
            # Check if the whole paragraph is an image
            if joined.strip().startswith('<img ') and joined.count('<img') == 1 and len(pbuf) == 1:
                out.append(f'<figure>{joined}</figure>')
            else:
                out.append(f'<p>{joined}</p>')
            pbuf.clear()

    def close_state():
        flush_p()
        nonlocal state
        if state == 'bq':
            out.append('</blockquote>')
        elif state == 'table':
            out.append('</tbody></table></div>')
        elif state == 'ul':
            out.append('</ul>')
        state = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ── Horizontal rule ──
        if re.match(r'^---+\s*$', stripped):
            close_state()
            out.append('<hr>')
            i += 1; continue

        # ── Headers ──
        m = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if m:
            close_state()
            lvl = len(m.group(1))
            raw = m.group(2)
            slug = f"ch{chapter_num}-" + re.sub(r'[^a-z0-9]+', '-', raw.lower()).strip('-')
            html_text = inline(raw)
            cls = ' class="chapter-title"' if lvl == 1 else ''
            out.append(f'<h{lvl} id="{slug}"{cls}>{html_text}</h{lvl}>')
            if lvl <= 2:
                toc_entries.append((lvl, slug, raw))
            i += 1; continue

        # ── Blockquote ──
        if stripped.startswith('> ') or (stripped == '>' and state == 'bq'):
            if state != 'bq':
                close_state()
                state = 'bq'
                out.append('<blockquote>')
            content = stripped[2:] if stripped.startswith('> ') else ''
            if content:
                out.append(f'<p>{inline(content)}</p>')
            i += 1; continue
        if state == 'bq' and stripped == '':
            # Check if next non-empty line is also blockquote
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines) and lines[j].strip().startswith('>'):
                out.append('')
                i += 1; continue
            else:
                close_state()
                i += 1; continue

        # ── Table ──
        if '|' in stripped and stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            # Separator row?
            if all(re.match(r'^[-:]+$', c) for c in cells if c):
                i += 1; continue
            if state != 'table':
                close_state()
                state = 'table'
                out.append('<div class="table-wrap"><table><thead><tr>')
                for cell in cells:
                    out.append(f'<th>{inline(cell)}</th>')
                out.append('</tr></thead><tbody>')
                i += 1; continue
            out.append('<tr>')
            for cell in cells:
                out.append(f'<td>{inline(cell)}</td>')
            out.append('</tr>')
            i += 1; continue

        # ── Unordered list ──
        m = re.match(r'^[-*]\s+(.+)$', stripped)
        if m:
            if state != 'ul':
                close_state()
                state = 'ul'
                out.append('<ul>')
            out.append(f'<li>{inline(m.group(1))}</li>')
            i += 1; continue
        # List continuation (indented)
        if state == 'ul' and line.startswith('  ') and stripped:
            if out and '</li>' in out[-1]:
                out[-1] = out[-1].replace('</li>', ' ' + inline(stripped) + '</li>')
            i += 1; continue

        # ── Empty line ──
        if stripped == '':
            if state:
                close_state()
            elif pbuf:
                flush_p()
            i += 1; continue

        # ── Regular text (paragraph) ──
        if state and state not in (None,):
            close_state()
        pbuf.append(stripped)
        i += 1

    close_state()
    return '\n'.join(out), toc_entries


# ── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
:root {
    --text: #2C3E50;
    --text-light: #6B7B8D;
    --bg: #FAF8F5;
    --card: #FFFFFF;
    --accent: #A0522D;
    --accent-light: #E8D5C4;
    --blue: #2C5F7C;
    --border: #E8E0D8;
    --green: #3A7D44;
    --serif: Georgia, 'Palatino Linotype', 'Book Antiqua', serif;
    --sans: 'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', sans-serif;
}

*, *::before, *::after { box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
    font-family: var(--serif);
    color: var(--text);
    background: var(--bg);
    line-height: 1.75;
    margin: 0;
    padding: 0;
    font-size: 17px;
    -webkit-font-smoothing: antialiased;
}

.container {
    max-width: 760px;
    margin: 0 auto;
    padding: 1.5rem 1.5rem 4rem;
}

/* ── Cover ─────────────────────────────────────────────── */
.cover {
    text-align: center;
    padding: 4rem 2rem 3rem;
    background: linear-gradient(135deg, var(--accent) 0%, var(--blue) 100%);
    color: white;
    margin-bottom: 2rem;
}
.cover h1 {
    font-family: var(--sans);
    font-size: 2.8rem;
    font-weight: 800;
    margin: 0 0 0.5rem;
    border: none;
    color: white;
    letter-spacing: -0.02em;
}
.cover .subtitle {
    font-size: 1.2rem;
    opacity: 0.9;
    font-style: italic;
    margin-bottom: 0.5rem;
}
.cover .dates {
    font-family: var(--sans);
    font-size: 0.95rem;
    opacity: 0.8;
    margin-top: 1rem;
}

/* ── TOC ───────────────────────────────────────────────── */
.toc {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem 2rem;
    margin-bottom: 2.5rem;
}
.toc h2 {
    font-family: var(--sans);
    font-size: 1.1rem;
    color: var(--accent);
    margin: 0 0 1rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.toc ol {
    margin: 0; padding: 0;
    list-style: none;
    counter-reset: toc;
}
.toc li {
    counter-increment: toc;
    margin-bottom: 0.4rem;
}
.toc li::before {
    content: counter(toc) ".";
    display: inline-block;
    width: 1.8rem;
    color: var(--text-light);
    font-family: var(--sans);
    font-size: 0.85rem;
}
.toc a {
    color: var(--text);
    text-decoration: none;
    font-size: 0.95rem;
    border-bottom: 1px solid transparent;
    transition: border-color 0.2s;
}
.toc a:hover { border-bottom-color: var(--accent); }

/* ── Typography ────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
    font-family: var(--sans);
    line-height: 1.3;
    margin-top: 2.5rem;
    margin-bottom: 0.8rem;
}
h1.chapter-title {
    font-size: 2rem;
    color: var(--accent);
    border-bottom: 3px solid var(--accent-light);
    padding-bottom: 0.5rem;
    margin-top: 3.5rem;
}
h2 { font-size: 1.4rem; color: var(--blue); }
h3 { font-size: 1.15rem; color: var(--text); }
h4, h5, h6 { font-size: 1rem; }

p { margin: 0 0 1rem; }

a { color: var(--blue); }

strong { color: var(--text); }

em { color: var(--text-light); font-style: italic; }

code {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.88em;
    background: var(--accent-light);
    padding: 0.15em 0.35em;
    border-radius: 3px;
}

hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 2.5rem 0;
}

/* ── Blockquotes ───────────────────────────────────────── */
blockquote {
    border-left: 4px solid var(--accent);
    background: var(--card);
    margin: 1.5rem 0;
    padding: 1rem 1.5rem;
    border-radius: 0 6px 6px 0;
    font-style: italic;
    color: var(--text-light);
}
blockquote p { margin-bottom: 0.5rem; }
blockquote p:last-child { margin-bottom: 0; }
blockquote strong { color: var(--text); }

/* ── Tables ────────────────────────────────────────────── */
.table-wrap {
    overflow-x: auto;
    margin: 1.5rem 0;
    -webkit-overflow-scrolling: touch;
}
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
    font-family: var(--sans);
}
thead { background: var(--accent); color: white; }
th {
    padding: 0.6rem 0.8rem;
    text-align: left;
    font-weight: 600;
    font-size: 0.85rem;
    white-space: nowrap;
}
td {
    padding: 0.5rem 0.8rem;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
}
tbody tr:hover { background: rgba(0,0,0,0.02); }

/* ── Lists ─────────────────────────────────────────────── */
ul {
    padding-left: 1.5rem;
    margin: 1rem 0;
}
li { margin-bottom: 0.4rem; }

/* ── Images ────────────────────────────────────────────── */
figure {
    margin: 2rem 0;
    text-align: center;
}
img {
    max-width: 100%;
    height: auto;
    border-radius: 6px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
img[src$=".svg"] {
    box-shadow: none;
    display: block;
    margin: 0 auto;
}

/* ── Back to top ───────────────────────────────────────── */
.back-top {
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    width: 40px;
    height: 40px;
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 50%;
    font-size: 1.2rem;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.3s;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
}
.back-top.visible { opacity: 0.7; }
.back-top:hover { opacity: 1; }

/* ── Language toggle ───────────────────────────────────── */
.lang-toggle {
    position: absolute;
    top: 1rem;
    right: 1.2rem;
    font-family: var(--sans);
    font-size: 0.85rem;
}
.lang-toggle a {
    color: rgba(255,255,255,0.75);
    text-decoration: none;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    border: 1px solid rgba(255,255,255,0.35);
    transition: background 0.2s;
}
.lang-toggle a:hover { background: rgba(255,255,255,0.15); color: white; }
.lang-toggle .active { color: white; font-weight: 700; border-color: white; }

/* ── Footer ────────────────────────────────────────────── */
.footer {
    text-align: center;
    padding: 2rem;
    font-size: 0.85rem;
    color: var(--text-light);
    font-family: var(--sans);
    border-top: 1px solid var(--border);
    margin-top: 3rem;
}

/* ── Mobile ────────────────────────────────────────────── */
@media (max-width: 600px) {
    body { font-size: 16px; }
    .container { padding: 1rem 1rem 3rem; }
    .cover { padding: 3rem 1.2rem 2rem; }
    .cover h1 { font-size: 2rem; }
    .cover .subtitle { font-size: 1rem; }
    h1.chapter-title { font-size: 1.5rem; margin-top: 2.5rem; }
    h2 { font-size: 1.2rem; }
    blockquote { padding: 0.8rem 1rem; margin: 1rem 0; }
    .toc { padding: 1rem 1.2rem; }
    th, td { padding: 0.4rem 0.5rem; font-size: 0.82rem; }
}

/* ── Print ─────────────────────────────────────────────── */
@media print {
    body {
        font-size: 11pt;
        background: white;
        color: black;
    }
    .container { max-width: 100%; padding: 0; }
    .cover {
        background: none !important;
        color: black;
        padding: 2rem 0;
        border-bottom: 3px solid #333;
    }
    .cover h1 { color: black; font-size: 24pt; }
    .cover .subtitle { color: #555; }
    .back-top { display: none; }
    a { color: black; text-decoration: underline; }
    a[href^="http"]::after {
        content: " (" attr(href) ")";
        font-size: 0.75em;
        color: #666;
    }
    h1.chapter-title {
        page-break-before: always;
        color: black;
        border-bottom-color: #333;
    }
    h1.chapter-title:first-of-type { page-break-before: auto; }
    img { max-width: 100%; box-shadow: none; }
    blockquote {
        border-left-color: #999;
        background: #f5f5f5;
    }
    thead { background: #eee; color: black; }
    .toc { border: 1px solid #ccc; }
    .toc a { color: black; }
    .footer { display: none; }
}
"""

# ── HTML template ────────────────────────────────────────────────────────────

def build_html(chapters_html, toc_entries):
    toc_items = []
    for lvl, slug, title in toc_entries:
        if lvl == 1:
            toc_items.append(f'<li><a href="#{slug}">{title}</a></li>')

    toc_html = '\n'.join(toc_items)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Catania — A Travel Guide for Your Family</title>
<meta name="description" content="A week in eastern Sicily: Catania, Mt Etna, Taormina, Syracuse, and the Cyclopean coast. 14–20 March 2026.">
<style>
{CSS}
</style>
</head>
<body>

<div class="cover" style="position:relative">
  <div class="lang-toggle">
    <span class="active">EN</span> &nbsp;
    <a href="index-nl.html">NL</a>
  </div>
  <h1>Catania</h1>
  <div class="subtitle">A Travel Guide for Your Family</div>
  <div class="dates">14–20 March 2026 · Eastern Sicily</div>
</div>

<div class="container">

<nav class="toc">
  <h2>Contents</h2>
  <ol>
    {toc_html}
  </ol>
</nav>

{chapters_html}

<div class="footer">
  Catania Travel Guide · March 2026<br>
  Photos from <a href="images/ATTRIBUTION.md">Wikimedia Commons</a> · Infographics generated with build-visuals.py
</div>

</div>

<a href="#" class="back-top" id="backTop" aria-label="Back to top">&uarr;</a>

<script>
// Back-to-top button
const btn = document.getElementById('backTop');
window.addEventListener('scroll', () => {{
  btn.classList.toggle('visible', window.scrollY > 600);
}});
</script>

</body>
</html>"""


# ── Image embedding ──────────────────────────────────────────────────────────

def embed_images(html, base_dir):
    """Replace all img src="images/..." with base64 data URIs."""
    def replacer(m):
        src = m.group(1)
        rest = m.group(2)
        img_path = base_dir / src
        if not img_path.exists():
            print(f"  [warn] missing image: {src}")
            return m.group(0)
        suffix = img_path.suffix.lower()
        # SVG files can be inlined as text (more efficient than base64)
        if suffix == ".svg":
            mime = "image/svg+xml"
        else:
            mime, _ = mimetypes.guess_type(str(img_path))
            if not mime:
                mime = "application/octet-stream"
        data = base64.b64encode(img_path.read_bytes()).decode("ascii")
        return f'<img src="data:{mime};base64,{data}"{rest}'

    # Match src="images/..." — capture src value and rest of attributes up to >
    return re.sub(r'<img src="([^"]+)"([^>]*>)', replacer, html)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    all_html = []
    all_toc = []

    for i, fname in enumerate(CHAPTERS):
        path = Path(fname)
        if not path.exists():
            print(f"  skip: {fname} (not found)")
            continue
        print(f"  {fname}")
        text = path.read_text(encoding="utf-8")
        html, toc = md_to_html(text, chapter_num=i+1)
        all_html.append(f'<article class="chapter" data-chapter="{i+1}">\n{html}\n</article>')
        all_toc.extend(toc)

    combined = '\n\n'.join(all_html)
    page = build_html(combined, all_toc)

    # Embed all images as base64 data URIs so the file is self-contained
    base_dir = Path(".")
    print("  Embedding images...")
    page = embed_images(page, base_dir)

    Path("index.html").write_text(page, encoding="utf-8")
    size_kb = len(page.encode("utf-8")) // 1024
    print(f"\n  Built: index.html ({size_kb}KB, fully self-contained)")
    print("  Open in browser or deploy to GitHub Pages.")


if __name__ == "__main__":
    main()
