#!/usr/bin/env python3
"""Print a compact view of the corpus for the daily pass.

    python3 tools/status.py              # summary + every page, one line each
    python3 tools/status.py --since 2026-08-01
    python3 tools/status.py --json

The point is that the daily pass can see the shape of the whole archive
without reading every note file, then open only the ones it needs.
"""

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notes as N  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="only notes dated on or after YYYY-MM-DD")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    corpus = N.load_notes()
    selected = [n for n in corpus if not args.since or n.date >= args.since]
    digests = {d for d, _ in N.load_digests()}
    tags = Counter(t for n in corpus for t in n.tags)

    if args.json:
        json.dump({
            "total": len(corpus),
            "selected": len(selected),
            "digests": sorted(digests, reverse=True),
            "tags": tags.most_common(),
            "notes": [{"id": n.id, "date": n.date, "title": n.title,
                       "tags": n.tags, "path": os.path.relpath(n.path, N.ROOT)}
                      for n in selected],
        }, sys.stdout, indent=2)
        print()
        return

    print("pages: %d   tags: %d   digests: %d"
          % (len(corpus), len(tags), len(digests)))
    if digests:
        print("last digest: %s" % max(digests))
    print("\ntags: %s" % ", ".join("%s(%d)" % (t, c) for t, c in tags.most_common()))
    header = "all pages" if not args.since else "pages since %s" % args.since
    print("\n%s (%d):" % (header, len(selected)))
    for note in selected:
        print("  %s  %-52s  [%s]"
              % (note.date, note.title[:52], ",".join(note.tags)))


if __name__ == "__main__":
    main()
