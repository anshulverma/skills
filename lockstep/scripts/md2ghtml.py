#!/usr/bin/env python3
"""Convert a humanized markdown doc to Google Docs ghtml.

Usage: md2ghtml.py SRC.md OUT.html   (writes the body, prints the title)
"""
import os
import re
import sys

import markdown


def _tldr(md: str) -> tuple[str, str]:
    m = re.search(r"^\| TL;DR \|\n\|-+\|\n((?:\|.*\|\n?)+)", md, re.M)
    if not m:
        return md, ""
    items = [line.strip()[1:-1].strip() for line in m.group(1).strip().split("\n")]
    lis = "".join(f"<li>{markdown.markdown(i)[3:-4]}</li>" for i in items)
    aside = f'<aside style="background-color:#E8F0FE"><b>TL;DR</b><ul>{lis}</ul></aside>'
    return md.replace(m.group(0), "@@TLDR@@\n\n"), aside


def convert(md: str, src_dir: str) -> tuple[str, str]:
    md = re.sub(r"<!-- humanize-context.*?-->\n*", "", md, flags=re.S)
    md, aside = _tldr(md)
    md = re.sub(r"!\[(.*?)\]\(([^)]+)\)",
                lambda m: f"@@IMG {m.group(1)}|{os.path.abspath(os.path.join(src_dir, m.group(2)))}@@", md)
    h = markdown.markdown(md, extensions=["tables", "fenced_code"])
    h = h.replace("<p>@@TLDR@@</p>", "<p></p>\n" + aside)
    h = re.sub(r"<p>@@IMG (.*?)\|(.*?)@@</p>",
               lambda m: f'<p style="text-align:center"><img src="file://{m.group(2)}" alt="{m.group(1)}"></p>', h)
    h = re.sub(r"<p><em>(Figure \d+\..*?)</em></p>", r'<p style="text-align:center"><i>\1</i></p>', h)
    m = re.search(r"<h1>(.*?)</h1>", h)
    title = re.sub(r"<[^>]+>", "", m.group(1)) if m else ""
    h = re.sub(r"<h1>(.*?)</h1>", r'<p data-style="TITLE">\1</p>', h, count=1)
    h = h.replace("<strong>", "<b>").replace("</strong>", "</b>").replace("<em>", "<i>").replace("</em>", "</i>")
    h = re.sub(r"<pre><code[^>]*>", "<pre>", h).replace("</code></pre>", "</pre>")
    h = re.sub(r"</table>\n?", "</table>\n<p></p>\n", h)
    h = re.sub(r"</(ul|ol)>\n(?!<p></p>)", r"</\1>\n<p></p>\n", h)
    return title, h + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    src, out = argv
    title, body = convert(open(src).read(), os.path.dirname(os.path.abspath(src)))
    open(out, "w").write(body)
    print(title)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
