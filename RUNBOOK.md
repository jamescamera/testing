# Daily pass runbook

This is the procedure the scheduled bot follows. It is written for a fresh
session that has never seen this repo before, so it assumes nothing.

## What this repo is

A capture-and-read system for handwritten ad-idea notes.

```
photo on phone -> Google Drive folder -> ingest -> notes/*.md -> digest -> site/index.html
```

- `notes/` one markdown file per photographed page. The corpus.
- `images/` archived page photos, downscaled. `images/thumbs/` feeds the site.
- `digests/` one file per daily pass, `YYYY-MM-DD.md`.
- `state/ingested.json` Drive file IDs already processed, so pages are never
  ingested twice.
- `site/index.html` generated archive, published as an Artifact.
- `tags.md` the controlled tag vocabulary. Read it before tagging.

## Setup

```bash
pip install pillow --quiet     # thumbnails; ingest still works without it
```

## Step 1 - Ingest

If this session has no `mcp__Google_Drive__*` tools, the Drive connector is
not attached to the Routine. Do not guess at what might have arrived: skip
to step 2, work only with notes already in the repo, and say plainly in the
digest that ingest was skipped for lack of Drive access.

Find new page photos in the Google Drive folder **`Ad Notes Inbox`**
(folder ID `1PNjnnaPTj599ZF7jA1oKLOblzXZpsbCT`, on the connected Google
account). Query it by `parentId = '1PNjnnaPTj599ZF7jA1oKLOblzXZpsbCT'`.

1. Read `state/ingested.json`. Every Drive file ID in there is already done.
2. List image files in the Drive folder. Skip any ID already in state.
3. For each new image, in date order oldest first:
   - Download it locally.
   - **Look at it.** Transcribe and interpret it against the rules below.
   - Write the note:
     `echo '<payload json>' | python3 tools/new_note.py`
   - Archive the image: `python3 tools/add_image.py <local-file> <note-id>`
     (the note ID is printed by the previous step, minus path and `.md`)
   - Record the Drive file ID in `state/ingested.json` with the note ID.

If there are no new images, skip to step 3 and note it — do not invent
content, and do not write a digest that pretends pages arrived.

### Transcription rules

The transcription is a record, not a rewrite. It is the one part of a note
that must be trustworthy years from now.

- **Transcribe what is on the page, not what you think was meant.** If the
  page says "Silicon tubes", the transcription says "Silicon tubes". Put the
  likely intent in a parenthetical, not in place of the words.
- **Mark every uncertain reading** as uncertain, with your best guess and
  what makes it doubtful. A confidently wrong transcription is much worse
  than a flagged unclear one.
- **Preserve the page's structure**: what is underlined, circled, ticked,
  crossed out, boxed, or connected by an arrow. Emphasis is information —
  it is where the attention went.
- **Record revisions.** Something written over, struck through, or corrected
  tells you the thinking moved. Say so, and say what it moved from if it is
  legible.
- **Describe the sketches properly** in their own section: what the marks
  are, how they relate spatially, and what they appear to depict. Do not
  skip a drawing because it is crude. Note when a shape recurs.
- Ignore show-through from other pages, the desk, the pen, the notebook.

### The Reading section

This is the section that earns the system its keep. Transcription is
clerical; the reading is the work.

- **Look for the single idea underneath the fragments.** Pages like these
  are usually one thought written down in pieces, not a list of separate
  thoughts. Say what the pieces add up to.
- **Say which fragment is strongest and which is weakest,** and why. Be
  direct about it. Category words ("innovation", "trust", "journey") are
  almost always the weakest thing on a page.
- **Separate what is on the page from what you inferred.** Inference is
  welcome — flag it as inference.
- Set `confidence` in the front-matter honestly: `high` when the page is
  legible and the meaning is plain, `low` when you are largely guessing.

### Tagging

Read `tags.md` first and prefer existing tags. Three to six tags per page.
If you add a new tag, add it to `tags.md` in the same commit.

## Step 2 - Digest

```bash
python3 tools/status.py                    # shape of the whole archive
python3 tools/status.py --since <30d ago>  # the recent window
```

Read today's new notes in full, plus any older note the new ones touch.
Write `digests/YYYY-MM-DD.md`. No front-matter; start with a `##` heading.

A digest is worth reading only if it says something the notes do not say
individually. Aim for four short sections, and cut any that has nothing
real in it:

- **What came in** — one line per new page. Skip entirely if nothing arrived.
- **Threads** — the actual product. Ideas recurring across pages, especially
  pages weeks apart. Name the note dates so they can be found. A thread
  that appears on three pages is a conviction, and worth saying so.
- **Tensions** — where pages contradict each other, or where a newer page
  quietly abandons something an older one was certain about. These are the
  most useful thing in the archive and the easiest to miss.
- **Worth a push** — one or two concrete provocations. Not "consider
  exploring the patient journey" — something with an edge on it, that could
  be argued with.

Rules:
- **Never invent a connection.** If two pages are unrelated, they are
  unrelated. A digest that manufactures threads teaches you to distrust it,
  and then the whole system is dead.
- **A quiet day is a legitimate result.** Three honest lines beat a page of
  filler. If nothing connected, say nothing connected.
- Do not restate the transcription. It is one click away on the site.
- Do not re-tell the same thread every day in the same words. If a thread
  has not moved, either say it has not moved, or leave it out.

## Step 3 - Publish

```bash
python3 tools/build_site.py
```

Then republish the Artifact **to the same URL**
(`https://claude.ai/code/artifact/0ad78c7e-dc5b-46dc-abe1-1171c473431c`,
passed as the `url` parameter) — pass the existing URL as
`url`, do not create a second artifact. The URL is recorded in `README.md`.
Keep the title and favicon unchanged.

## Step 4 - Commit

```bash
git add -A
git commit -m "Daily pass YYYY-MM-DD: N pages ingested"
git push -u origin claude/ad-notes-organization-0hfuoh
```

If nothing changed at all, do not commit and do not republish. Silence is
the correct output for an empty day.
