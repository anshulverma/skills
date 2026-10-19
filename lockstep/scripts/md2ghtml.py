#!/usr/bin/env python3
"""Convert a humanized markdown doc to Google Docs ghtml.

Usage: md2ghtml.py SRC.md OUT.html   (writes the body, prints the title)
"""
import html
import os
import re
import sys
from pathlib import Path

import markdown


def _tldr(md: str) -> tuple[str, str]:
    m = re.search(r"^\| TL;DR \|\n\|-+\|\n((?:\|.*\|\n?)+)", md, re.M)
    if not m:
        return md, ""
    items = [line.strip()[1:-1].strip() for line in m.group(1).strip().split("\n")]
    lis = "".join(f"<li>{markdown.markdown(i)[3:-4]}</li>" for i in items)
    aside = f'<aside style="background-color:#E8F0FE"><b>TL;DR</b><ul>{lis}</ul></aside>'
    return md.replace(m.group(0), "@@TLDR@@\n\n"), aside


IMG = re.compile(r"!\[([^\]]*)\]\(([^()\s]*(?:\([^()]*\)[^()\s]*)*)\)")


def _img(m: re.Match, src_dir: str) -> str:
    """Centered paragraph when the image is the whole line (m.string is that line), inline tag otherwise."""
    alt, path = m.group(1), m.group(2)
    url = path if re.match(r"^([a-z]+://|data:)", path) else Path(os.path.join(src_dir, path)).resolve().as_uri()
    tag = f'<img src="{html.escape(url, quote=True)}" alt="{html.escape(alt, quote=True)}">'
    return f'<p style="text-align:center">{tag}</p>' if m.group(0) == m.string.strip() else tag


def _outside_fences(md: str, fn) -> str:
    """Apply fn to every chunk of md that is not inside a ``` fence."""
    parts = re.split(r"(^```.*?^```[^\n]*$)", md, flags=re.M | re.S)
    return "".join(p if i % 2 else fn(p) for i, p in enumerate(parts))


def convert(md: str, src_dir: str) -> tuple[str, str]:
    md = re.sub(r"<!-- humanize-context.*?-->\n*", "", md, flags=re.S)
    aside = ""

    def prose(chunk: str) -> str:
        nonlocal aside
        if not aside:
            chunk, aside = _tldr(chunk)
        return "\n".join(IMG.sub(lambda m: _img(m, src_dir), line) for line in chunk.split("\n"))

    md = _outside_fences(md, prose)
    h = markdown.markdown(md, extensions=["tables", "fenced_code"])
    h = h.replace("<p>@@TLDR@@</p>", "<p></p>\n" + aside)
    h = re.sub(r"<p>(<p style=\"text-align:center\"><img [^>]*></p>)</p>", r"\1", h)
    h = re.sub(r"<p><em>(Figure \d+\..*?)</em></p>", r'<p style="text-align:center"><i>\1</i></p>', h)
    m = re.search(r"<h1>(.*?)</h1>", h)
    title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))) if m else ""
    h = re.sub(r"<h1>(.*?)</h1>", r'<p data-style="TITLE">\1</p>', h, count=1)
    h = h.replace("<strong>", "<b>").replace("</strong>", "</b>").replace("<em>", "<i>").replace("</em>", "</i>")
    h = re.sub(r"<pre><code[^>]*>", "<pre>", h).replace("</code></pre>", "</pre>")
    h = re.sub(r"</table>\n?", "</table>\n<p></p>\n", h)
    h = re.sub(r"</(ul|ol)>\n(?!<p></p>|</li>)", r"</\1>\n<p></p>\n", h)
    return title, h + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    src, out = argv
    with open(src, encoding="utf-8") as f:
        title, body = convert(f.read(), os.path.dirname(os.path.abspath(src)))
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    print(title)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
