#!/usr/bin/env python3
"""Build site/index.html from the note and digest corpus.

    python3 tools/build_site.py

The output is a single self-contained file: thumbnails are inlined as data
URIs, and there are no external requests except the Google Fonts stylesheet.
"""

import base64
import collections
import datetime as dt
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import markdown  # noqa: E402
import notes as N  # noqa: E402

OUT_PATH = os.path.join(N.ROOT, "site", "index.html")
SIZE_BUDGET_BYTES = 12 * 1024 * 1024  # artifact cap is 16MB; leave headroom

CSS = """
:root {
  --ground: #FBFBFD;
  --surface: #FFFFFF;
  --surface-sunk: #F2F3F7;
  --ink: #14171D;
  --ink-soft: #3D4552;
  --muted: #6E7686;
  --line: #E0E3EB;
  --line-strong: #C7CCD8;
  --accent: #D9500A;
  --accent-soft: #FBEDE4;
  --shadow: 0 1px 2px rgba(20, 23, 29, .05), 0 8px 24px -16px rgba(20, 23, 29, .28);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground: #0E1014;
    --surface: #161A21;
    --surface-sunk: #1D222B;
    --ink: #E9ECF2;
    --ink-soft: #B7BECB;
    --muted: #8A93A3;
    --line: #262C36;
    --line-strong: #38404D;
    --accent: #FF7A3D;
    --accent-soft: #2A1B12;
    --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 8px 24px -16px rgba(0, 0, 0, .8);
  }
}
:root[data-theme="dark"] {
  --ground: #0E1014;
  --surface: #161A21;
  --surface-sunk: #1D222B;
  --ink: #E9ECF2;
  --ink-soft: #B7BECB;
  --muted: #8A93A3;
  --line: #262C36;
  --line-strong: #38404D;
  --accent: #FF7A3D;
  --accent-soft: #2A1B12;
  --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 8px 24px -16px rgba(0, 0, 0, .8);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: Archivo, "Helvetica Neue", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

.mono, .meta, .chip, .count, .stat-value {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}

.wrap { max-width: 1180px; margin: 0 auto; padding: 0 24px 96px; }

/* ---------- masthead ---------- */
.masthead {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 56px 0 28px;
  border-bottom: 2px solid var(--ink);
}
.masthead h1 {
  margin: 0;
  font-size: clamp(2rem, 5vw, 3.1rem);
  font-weight: 700;
  letter-spacing: -.03em;
  line-height: 1.02;
  text-wrap: balance;
}
.masthead h1 .accent { color: var(--accent); }
.tagline {
  margin: 10px 0 0;
  max-width: 46ch;
  color: var(--muted);
  font-size: .95rem;
}
.stats { display: flex; gap: 28px; }
.stat-label {
  display: block;
  font-size: .68rem;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--muted);
}
.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* ---------- layout ---------- */
.columns {
  display: grid;
  grid-template-columns: 232px minmax(0, 1fr);
  gap: 48px;
  align-items: start;
  padding-top: 36px;
}
.rail { position: sticky; top: 24px; display: flex; flex-direction: column; gap: 26px; }
.rail-group h2 {
  margin: 0 0 12px;
  font-size: .68rem;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}

#search {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--line-strong);
  border-radius: 3px;
  background: var(--surface);
  color: var(--ink);
  font: inherit;
  font-size: .9rem;
}
#search::placeholder { color: var(--muted); }
#search:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }

.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  border: 1px solid var(--line-strong);
  background: var(--surface);
  color: var(--ink-soft);
  border-radius: 999px;
  padding: 4px 11px;
  font-size: .73rem;
  cursor: pointer;
  transition: background .12s ease, color .12s ease, border-color .12s ease;
}
.chip:hover { border-color: var(--accent); color: var(--accent); }
.chip:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.chip[aria-pressed="true"] {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.chip .n { opacity: .55; margin-left: 5px; font-variant-numeric: tabular-nums; }

/* ---------- digest ---------- */
.digest {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: 3px;
  padding: 26px 30px;
  margin-bottom: 44px;
  box-shadow: var(--shadow);
}
.digest-label {
  font-size: .68rem;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 600;
}
.digest h3 { margin: 6px 0 14px; font-size: 1.3rem; letter-spacing: -.015em; }
.digest .prose { font-size: .95rem; }

/* ---------- notes ---------- */
.note {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 24px;
  padding: 30px 0;
  border-top: 1px solid var(--line);
}
.note:first-of-type { border-top: 2px solid var(--ink); }
.note[hidden] { display: none; }
.note-head { min-width: 0; }
.meta {
  font-size: .72rem;
  letter-spacing: .06em;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.note h3 {
  margin: 6px 0 12px;
  font-size: 1.3rem;
  font-weight: 600;
  letter-spacing: -.018em;
  line-height: 1.25;
  text-wrap: balance;
}
.note-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
.tag {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: .68rem;
  color: var(--ink-soft);
  background: var(--surface-sunk);
  border-radius: 2px;
  padding: 3px 8px;
}
.thumb {
  width: 168px;
  border: 1px solid var(--line);
  border-radius: 2px;
  display: block;
  background: var(--surface);
}
figure { margin: 0; }
figcaption {
  margin-top: 6px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: .64rem;
  color: var(--muted);
  text-align: right;
}

/* transcribed content is set in the serif; system chrome stays sans */
.prose {
  font-family: "IBM Plex Serif", Georgia, serif;
  color: var(--ink-soft);
  max-width: 68ch;
}
.prose p { margin: 0 0 .85em; }
.prose ul, .prose ol { margin: 0 0 .85em; padding-left: 1.25em; }
.prose li { margin-bottom: .3em; }
.prose strong { color: var(--ink); font-weight: 600; }
.prose code {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: .88em;
  background: var(--surface-sunk);
  padding: 1px 5px;
  border-radius: 2px;
}
.prose a { color: var(--accent); }

.reading { margin-bottom: 14px; }

details { border-top: 1px solid var(--line); }
details summary {
  cursor: pointer;
  list-style: none;
  padding: 9px 0;
  font-size: .74rem;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}
details summary::-webkit-details-marker { display: none; }
details summary::before {
  content: "+";
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: var(--accent);
  font-size: .95rem;
  line-height: 1;
}
details[open] summary::before { content: "\\2212"; }
details summary:hover { color: var(--accent); }
details summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
details .prose { padding: 4px 0 18px; font-size: .92rem; }

.empty {
  padding: 48px 0;
  color: var(--muted);
  font-size: .95rem;
}
.empty[hidden] { display: none; }

footer {
  margin-top: 64px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: .72rem;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  justify-content: space-between;
}

@media (max-width: 860px) {
  .columns { grid-template-columns: 1fr; gap: 32px; }
  .rail { position: static; }
  .note { grid-template-columns: 1fr; }
  .thumb { width: 100%; max-width: 260px; }
  figcaption { text-align: left; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""

JS = """
(function () {
  var search = document.getElementById('search');
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var notes = Array.prototype.slice.call(document.querySelectorAll('.note'));
  var empty = document.getElementById('empty');
  var counter = document.getElementById('shown-count');
  var active = null;

  function apply() {
    var q = search.value.trim().toLowerCase();
    var shown = 0;
    notes.forEach(function (note) {
      var tags = (note.dataset.tags || '').split(' ');
      var byTag = !active || tags.indexOf(active) !== -1;
      var byText = !q || (note.dataset.haystack || '').indexOf(q) !== -1;
      var visible = byTag && byText;
      note.hidden = !visible;
      if (visible) { shown++; }
    });
    empty.hidden = shown !== 0;
    counter.textContent = shown;
  }

  search.addEventListener('input', apply);
  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      active = active === chip.dataset.tag ? null : chip.dataset.tag;
      chips.forEach(function (c) {
        c.setAttribute('aria-pressed', String(c.dataset.tag === active));
      });
      apply();
    });
  });
  apply();
})();
"""


def data_uri(path):
    with open(path, "rb") as handle:
        return "data:image/jpeg;base64," + base64.b64encode(handle.read()).decode()


def note_html(note, with_thumbs=True):
    tags = note.tags
    haystack = " ".join([
        note.title, note.date, " ".join(tags),
        note.section("Transcription"), note.section("Sketches"),
        note.section("Reading"), note.section("Open questions"),
    ]).lower()

    thumb = note.thumb_path() if with_thumbs else None
    figure = ""
    if thumb:
        figure = (
            '<figure><img class="thumb" src="%s" alt="Photograph of the '
            'handwritten page: %s" loading="lazy"><figcaption>original page'
            '</figcaption></figure>'
            % (data_uri(thumb), html.escape(note.title, quote=True))
        )

    chips = "".join('<span class="tag">%s</span>' % html.escape(t) for t in tags)

    blocks = []
    reading = note.section("Reading")
    if reading and reading != "_not captured_":
        blocks.append('<div class="prose reading">%s</div>' % markdown.render(reading))
    for heading in ("Transcription", "Sketches", "Open questions", "Threads"):
        body = note.section(heading)
        if not body or body == "_not captured_":
            continue
        blocks.append(
            "<details><summary>%s</summary><div class=\"prose\">%s</div></details>"
            % (html.escape(heading), markdown.render(body))
        )

    return (
        '<article class="note" data-tags="%s" data-haystack="%s">'
        '<div class="note-head">'
        '<div class="meta">%s &middot; %s</div>'
        '<h3>%s</h3>'
        '<div class="note-tags">%s</div>'
        '%s</div>%s</article>'
        % (
            html.escape(" ".join(tags), quote=True),
            html.escape(haystack, quote=True),
            html.escape(note.date),
            html.escape(str(note.meta.get("confidence", "")) + " confidence"),
            html.escape(note.title),
            chips,
            "".join(blocks),
            figure,
        )
    )


def build(with_thumbs=True):
    all_notes = N.load_notes()
    digests = N.load_digests()

    tag_counts = collections.Counter()
    for note in all_notes:
        tag_counts.update(note.tags)

    dates = [n.date for n in all_notes if n.date]
    span = "%s to %s" % (min(dates), max(dates)) if dates else "no pages yet"

    chips = "".join(
        '<button class="chip" type="button" data-tag="%s" aria-pressed="false">'
        '%s<span class="n">%d</span></button>'
        % (html.escape(tag, quote=True), html.escape(tag), count)
        for tag, count in sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ) or '<p class="meta">No tags yet.</p>'

    if digests:
        date, body = digests[0]
        digest_block = (
            '<section class="digest"><div class="digest-label">Latest read</div>'
            '<h3>%s</h3><div class="prose">%s</div></section>'
            % (html.escape(date), markdown.render(body))
        )
    else:
        digest_block = (
            '<section class="digest"><div class="digest-label">Latest read</div>'
            '<h3>No digest yet</h3><div class="prose"><p>The daily pass has not '
            'run against this corpus yet. Once it does, the connections it finds '
            'across pages appear here.</p></div></section>'
        )

    body_notes = "".join(note_html(n, with_thumbs) for n in all_notes)

    return """<title>Ad Notes Archive</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Serif:ital,wght@0,400;0,600;1,400&display=swap">
<style>%(css)s</style>
<div class="wrap">
  <header class="masthead">
    <div>
      <h1>Ad Notes<br><span class="accent">Archive</span></h1>
      <p class="tagline">Every page of scribbled thinking, transcribed, tagged
        and read back for the threads running between them.</p>
    </div>
    <div class="stats">
      <div><span class="stat-label">Pages</span><span class="stat-value">%(count)d</span></div>
      <div><span class="stat-label">Tags</span><span class="stat-value">%(tags)d</span></div>
      <div><span class="stat-label">Digests</span><span class="stat-value">%(digests)d</span></div>
    </div>
  </header>

  <div class="columns">
    <aside class="rail">
      <div class="rail-group">
        <h2>Search</h2>
        <input id="search" type="search" placeholder="ink, claims, anything&hellip;"
               aria-label="Search all pages">
      </div>
      <div class="rail-group">
        <h2>Filter by tag</h2>
        <div class="chips">%(chips)s</div>
      </div>
      <div class="rail-group">
        <h2>Showing</h2>
        <p class="meta"><span id="shown-count">%(count)d</span> of %(count)d pages<br>%(span)s</p>
      </div>
    </aside>

    <main>
      %(digest)s
      %(notes)s
      <p class="empty" id="empty" hidden>Nothing matches that. Clear the search
        or the active tag to see everything again.</p>
    </main>
  </div>

  <footer>
    <span>Built %(built)s</span>
    <span>Handwriting is the source of truth &mdash; transcriptions may misread it.</span>
  </footer>
</div>
<script>%(js)s</script>
""" % {
        "css": CSS,
        "js": JS,
        "count": len(all_notes),
        "tags": len(tag_counts),
        "digests": len(digests),
        "span": html.escape(span),
        "chips": chips,
        "digest": digest_block,
        "notes": body_notes or "",
        "built": dt.date.today().isoformat(),
    }


def main():
    page = build(with_thumbs=True)
    if len(page.encode("utf-8")) > SIZE_BUDGET_BYTES:
        page = build(with_thumbs=False)
        print("size budget exceeded - rebuilt without embedded thumbnails")
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(page)
    print("%s (%dKB)" % (OUT_PATH, len(page.encode("utf-8")) // 1024))


if __name__ == "__main__":
    main()
