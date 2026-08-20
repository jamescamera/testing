"""A small markdown-to-HTML renderer.

Covers only what the notes and digests actually use: headings, bullet and
numbered lists, bold, italic, inline code, links, and paragraphs. Written by
hand so the site build stays dependency-free.
"""

import html
import re

_INLINE = [
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])"), r"<em>\1</em>"),
    (re.compile(r"(?<![\w_])_([^_\n]+)_(?![\w_])"), r"<em>\1</em>"),
    (re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)"),
     r'<a href="\2" rel="noopener noreferrer" target="_blank">\1</a>'),
]


def inline(text):
    out = html.escape(text, quote=False)
    for pattern, repl in _INLINE:
        out = pattern.sub(repl, out)
    return out


def render(text, base_heading=3):
    """Render markdown to an HTML fragment."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    out, list_stack, para = [], [], []

    def flush_para():
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para).strip()))
            para.clear()

    def close_lists(depth=0):
        while len(list_stack) > depth:
            out.append("</%s>" % list_stack.pop())

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_para()
            close_lists()
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_para()
            close_lists()
            level = min(base_heading + len(heading.group(1)) - 1, 6)
            out.append("<h%d>%s</h%d>" % (level, inline(heading.group(2)), level))
            continue

        bullet = re.match(r"^([-*])\s+(.*)$", stripped)
        ordered = re.match(r"^(\d+)[.)]\s+(.*)$", stripped)
        if bullet or ordered:
            flush_para()
            tag = "ul" if bullet else "ol"
            if not list_stack:
                list_stack.append(tag)
                out.append("<%s>" % tag)
            elif list_stack[-1] != tag:
                close_lists()
                list_stack.append(tag)
                out.append("<%s>" % tag)
            out.append("<li>%s</li>" % inline((bullet or ordered).group(2)))
            continue

        if list_stack:
            # continuation line inside the current list item
            out[-1] = out[-1][:-5] + " " + inline(stripped) + "</li>"
            continue

        para.append(stripped)

    flush_para()
    close_lists()
    return "\n".join(out)
