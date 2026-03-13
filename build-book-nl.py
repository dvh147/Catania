#!/usr/bin/env python3
"""
build-book-nl.py
Builds the Dutch version of the Catania travel guide → index-nl.html
"""

import importlib.util
from pathlib import Path

# Import helpers from build-book.py
spec = importlib.util.spec_from_file_location("build_book", Path("build-book.py"))
build_book = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_book)

md_to_html = build_book.md_to_html
embed_images = build_book.embed_images
CSS = build_book.CSS

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


def build_html_nl(chapters_html, toc_entries):
    toc_items = []
    for lvl, slug, title in toc_entries:
        if lvl == 1:
            toc_items.append(f'<li><a href="#{slug}">{title}</a></li>')

    toc_html = '\n'.join(toc_items)

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Catania — Een reisgids voor het hele gezin</title>
<meta name="description" content="Een week in Oost-Sicilië: Catania, de Etna, Taormina, Syracuse en de Cyclopenkust. 14–20 maart 2026.">
<style>
{CSS}
</style>
</head>
<body>

<div class="cover" style="position:relative">
  <div class="lang-toggle">
    <a href="index.html">EN</a> &nbsp;
    <span class="active">NL</span>
  </div>
  <h1>Catania</h1>
  <div class="subtitle">Een reisgids voor het hele gezin</div>
  <div class="dates">14–20 maart 2026 · Oost-Sicilië</div>
</div>

<div class="container">

<nav class="toc">
  <h2>Inhoud</h2>
  <ol>
    {toc_html}
  </ol>
</nav>

{chapters_html}

<div class="footer">
  Catania Reisgids · maart 2026<br>
  Foto's van <a href="images/ATTRIBUTION.md">Wikimedia Commons</a> · Infographics gegenereerd met build-visuals.py
</div>

</div>

<a href="#" class="back-top" id="backTop" aria-label="Terug naar boven">&uarr;</a>

<script>
const btn = document.getElementById('backTop');
window.addEventListener('scroll', () => {{
  btn.classList.toggle('visible', window.scrollY > 600);
}});
</script>

</body>
</html>"""


def main():
    all_html = []
    all_toc = []

    for i, fname in enumerate(NL_CHAPTERS):
        path = Path(fname)
        if not path.exists():
            print(f"  skip: {fname} (not found)")
            continue
        print(f"  {fname}")
        text = path.read_text(encoding="utf-8")
        html, toc = md_to_html(text, chapter_num=i + 1)
        all_html.append(f'<article class="chapter" data-chapter="{i+1}">\n{html}\n</article>')
        all_toc.extend(toc)

    combined = '\n\n'.join(all_html)
    page = build_html_nl(combined, all_toc)

    base_dir = Path(".")
    print("  Afbeeldingen inbedden...")
    page = embed_images(page, base_dir)

    Path("index-nl.html").write_text(page, encoding="utf-8")
    size_kb = len(page.encode("utf-8")) // 1024
    print(f"\n  Gebouwd: index-nl.html ({size_kb}KB, volledig zelfstandig)")


if __name__ == "__main__":
    main()
