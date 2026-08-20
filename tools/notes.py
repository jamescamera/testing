"""Shared note-corpus helpers.

A note is a markdown file in notes/ with a small YAML-ish front-matter block.
The parser here deliberately supports only the subset we emit (scalars and
lists of plain strings) so the tools have no third-party dependencies.
"""

import datetime as dt
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_DIR = os.path.join(ROOT, "notes")
IMAGES_DIR = os.path.join(ROOT, "images")
THUMBS_DIR = os.path.join(IMAGES_DIR, "thumbs")
DIGESTS_DIR = os.path.join(ROOT, "digests")
STATE_PATH = os.path.join(ROOT, "state", "ingested.json")

SECTIONS = ["Transcription", "Sketches", "Reading", "Threads", "Open questions"]


def slugify(text, max_len=48):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:max_len].strip("-") or "untitled"


def _parse_scalar(raw):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [p.strip().strip("\"'") for p in inner.split(",") if p.strip()]
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def parse_front_matter(text):
    """Return (meta_dict, body_str). Missing front-matter yields ({}, text)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")

    meta, pending_key = {}, None
    for line in block.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith(("  - ", "- ")) and pending_key:
            meta[pending_key].append(_parse_scalar(line.split("- ", 1)[1]))
            continue
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        if not raw.strip():
            meta[key], pending_key = [], key
        else:
            meta[key], pending_key = _parse_scalar(raw), None
    return meta, body


def dump_front_matter(meta):
    lines = ["---"]
    for key, value in meta.items():
        if value is None or value == "":
            continue
        if isinstance(value, (list, tuple)):
            if not value:
                continue
            lines.append("%s: [%s]" % (key, ", ".join(str(v) for v in value)))
        else:
            text = str(value)
            quote = any(ch in text for ch in ":#[]{}") or text != text.strip()
            lines.append('%s: "%s"' % (key, text.replace('"', "'")) if quote
                         else "%s: %s" % (key, text))
    lines.append("---")
    return "\n".join(lines) + "\n"


def split_sections(body):
    """Split a note body into {heading: content} for its '## ' headings."""
    out, current, buf = {}, None, []
    for line in body.split("\n"):
        if line.startswith("## "):
            if current:
                out[current] = "\n".join(buf).strip()
            current, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if current:
        out[current] = "\n".join(buf).strip()
    return out


class Note:
    def __init__(self, path, meta, body):
        self.path = path
        self.meta = meta
        self.body = body
        self.sections = split_sections(body)

    @property
    def id(self):
        return self.meta.get("id") or os.path.basename(self.path)[:-3]

    @property
    def date(self):
        return str(self.meta.get("date", ""))

    @property
    def title(self):
        return self.meta.get("title") or self.id

    @property
    def tags(self):
        tags = self.meta.get("tags", [])
        return tags if isinstance(tags, list) else [tags]

    def section(self, name):
        return self.sections.get(name, "")

    def thumb_path(self):
        src = self.meta.get("source_image")
        if not src:
            return None
        candidate = os.path.join(THUMBS_DIR, os.path.basename(src))
        return candidate if os.path.exists(candidate) else None


def load_notes():
    """All notes, newest first."""
    notes = []
    if not os.path.isdir(NOTES_DIR):
        return notes
    for name in sorted(os.listdir(NOTES_DIR)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(NOTES_DIR, name)
        with open(path, encoding="utf-8") as handle:
            meta, body = parse_front_matter(handle.read())
        notes.append(Note(path, meta, body))
    notes.sort(key=lambda n: (n.date, n.id), reverse=True)
    return notes


def load_digests():
    """All digests, newest first, as (date, markdown) pairs."""
    out = []
    if not os.path.isdir(DIGESTS_DIR):
        return out
    for name in sorted(os.listdir(DIGESTS_DIR), reverse=True):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(DIGESTS_DIR, name), encoding="utf-8") as handle:
            out.append((name[:-3], handle.read().strip()))
    return out


def load_state():
    if not os.path.exists(STATE_PATH):
        return {"ingested": {}}
    with open(STATE_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")


def today():
    return dt.date.today().isoformat()
