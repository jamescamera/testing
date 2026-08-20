# Ad Notes

A capture-and-read system for messy handwritten ad-idea notes.

Take a photo of the page. Everything after that is automatic: the page gets
transcribed, the sketches described, the ideas tagged, and once a day the
whole archive is read back for the threads running between pages.

**Archive:** https://claude.ai/code/artifact/0ad78c7e-dc5b-46dc-abe1-1171c473431c

```
photo on phone -> Drive folder -> ingest -> notes/*.md -> daily digest -> archive page
```

## One-time setup

1. **Make the Drive folder.** Create a folder in Google Drive called exactly
   `Ad Notes Inbox`.
2. **Point your phone at it.** In the Google Drive app, set that folder as a
   destination you can share photos into. On iOS the fastest route is a
   Shortcut ("Save to Drive → Ad Notes Inbox") added to the share sheet or
   the lock screen, so a page is two taps from filed.
3. That is the whole capture side. No scanner, no Pi, no extra device to
   keep alive.

**Shooting the page:** flat, in daylight if you have it, whole page in frame
including the edges. Don't worry about glare or a wonky angle — those are
fine. What actually costs you is a cropped edge, because a fragment written
in the margin is often the best thing on the page.

## What you get per page

Each page becomes a markdown file in `notes/` with:

- **Transcription** — what is literally on the page, with uncertain readings
  flagged rather than smoothed over, and underlines, ticks, arrows and
  crossings-out recorded because that is where the attention went.
- **Sketches** — described properly, including how the shapes relate.
- **Reading** — what the fragments add up to, which is strongest, which is
  weakest, and what is inference rather than fact.
- **Tags** — from the controlled vocabulary in `tags.md`.
- **Open questions** — what the page asks and does not answer.

## The daily pass

A scheduled routine runs every morning and follows `RUNBOOK.md`: ingest new
photos, write the digest, rebuild the archive, commit. It republishes to the
same URL, so the link above never changes.

The digest is the real product. Transcribing is clerical; the value is in a
system that notices you have circled the same idea on three pages six weeks
apart, and tells you.

## Running it by hand

```bash
pip install pillow                       # thumbnails

python3 tools/status.py                  # what's in the archive
python3 tools/status.py --since 2026-08-01
python3 tools/build_site.py              # regenerate site/index.html
python3 tools/add_image.py photo.jpg <note-id>
cat payload.json | python3 tools/new_note.py
```

## Layout

| path | what |
| --- | --- |
| `notes/` | one markdown file per page — the corpus |
| `images/` | archived photos, downscaled; `thumbs/` feeds the archive page |
| `digests/` | one file per daily pass |
| `state/ingested.json` | Drive IDs already processed, so nothing doubles up |
| `site/index.html` | generated archive page |
| `tools/` | the scripts above, no third-party dependencies |
| `tags.md` | controlled tag vocabulary |
| `RUNBOOK.md` | the procedure the daily bot follows |

## A note on the transcriptions

Handwriting recognition is not solved, and yours is genuinely hard. The
transcriptions are good but not perfect, which is why the original photo is
archived next to every note and linked from the archive page. **The page is
the source of truth.** If a transcription looks wrong, it is wrong — fix the
markdown directly and it will survive every future rebuild.
