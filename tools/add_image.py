#!/usr/bin/env python3
"""Archive a captured page image into the repo.

    python3 tools/add_image.py <source-file> <note-id>

Writes a downscaled copy to images/<note-id>.jpg and a small thumbnail to
images/thumbs/<note-id>.jpg (the thumbnail is what the web archive embeds).
Without Pillow it falls back to copying the original and skips the thumbnail,
so ingest never hard-fails on a missing dependency.
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notes as N  # noqa: E402

FULL_MAX_PX = 1600
THUMB_MAX_PX = 420
JPEG_QUALITY = 78


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, note_id = sys.argv[1], sys.argv[2]
    if not os.path.exists(src):
        sys.exit("no such file: %s" % src)

    os.makedirs(N.IMAGES_DIR, exist_ok=True)
    os.makedirs(N.THUMBS_DIR, exist_ok=True)
    full = os.path.join(N.IMAGES_DIR, note_id + ".jpg")
    thumb = os.path.join(N.THUMBS_DIR, note_id + ".jpg")

    try:
        from PIL import Image, ImageOps
    except ImportError:
        shutil.copyfile(src, full)
        print("images/%s.jpg (original copied - install pillow for thumbnails)"
              % note_id)
        return

    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        full_img = img.copy()
        full_img.thumbnail((FULL_MAX_PX, FULL_MAX_PX), Image.LANCZOS)
        full_img.save(full, "JPEG", quality=JPEG_QUALITY, optimize=True)
        thumb_img = img.copy()
        thumb_img.thumbnail((THUMB_MAX_PX, THUMB_MAX_PX), Image.LANCZOS)
        thumb_img.save(thumb, "JPEG", quality=70, optimize=True)

    print("images/%s.jpg (%dKB), thumb (%dKB)"
          % (note_id, os.path.getsize(full) // 1024,
             os.path.getsize(thumb) // 1024))


if __name__ == "__main__":
    main()
