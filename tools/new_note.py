#!/usr/bin/env python3
"""Write a note file from a JSON payload on stdin.

    cat payload.json | python3 tools/new_note.py

Keeping the file format behind a script means every note comes out with the
same front-matter keys and the same section order, however it was ingested.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notes as N  # noqa: E402

FIELD_TO_SECTION = [
    ("transcription", "Transcription"),
    ("sketches", "Sketches"),
    ("reading", "Reading"),
    ("threads", "Threads"),
    ("open_questions", "Open questions"),
]


def build(payload):
    date = str(payload.get("date") or N.today())
    title = payload.get("title") or "Untitled page"
    note_id = payload.get("id") or "%s-%s" % (date, N.slugify(title))

    meta = {
        "id": note_id,
        "date": date,
        "title": title,
        "tags": payload.get("tags", []),
        "confidence": payload.get("confidence", "medium"),
        "source_image": payload.get("source_image", ""),
        "drive_file_id": payload.get("drive_file_id", ""),
        "captured_at": payload.get("captured_at", ""),
    }

    parts = [N.dump_front_matter(meta)]
    for field, heading in FIELD_TO_SECTION:
        content = (payload.get(field) or "").strip()
        if not content and heading in ("Threads", "Open questions"):
            continue
        parts.append("\n## %s\n\n%s\n" % (heading, content or "_not captured_"))
    return note_id, "".join(parts)


def main():
    payload = json.load(sys.stdin)
    note_id, text = build(payload)
    os.makedirs(N.NOTES_DIR, exist_ok=True)
    path = os.path.join(N.NOTES_DIR, note_id + ".md")
    if os.path.exists(path) and not payload.get("overwrite"):
        sys.exit("refusing to overwrite existing note: %s" % path)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(path)


if __name__ == "__main__":
    main()
