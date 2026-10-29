#!/usr/bin/env python3
"""Read the owner's dropdown chips from a fetched ghtml and report changes since the last tick.

Usage: chips.py DOC.html SEEN.json QPREFIX [--commit]

Prints a JSON list of changed chips, oldest-first by position in the doc:
  {"chip": "<title>", "kind": "answer"|"approval", "q": <n>|null, "option": "<selected text>"}
A chip still on its initial value ("Pick one", "Not yet") and never seen before is not a change.
--commit writes every current value to SEEN.json (atomic rename); run it after the changes are handled.
"""
import html
import json
import os
import re
import sys

INITIAL = {"Pick one", "Not yet"}


def read(s: str) -> list[tuple[str, str]]:
    titles = dict(re.findall(r'<datalist id="([^"]+)" title="([^"]+)"', s))
    out = []
    for m in re.finditer(r"<select data-dropdown([^>]*)>(.*?)</select>", s, re.S):
        attrs, body = m.groups()
        d = re.search(r'data-dropdown-definition-id="([^"]+)"', attrs)
        t = re.search(r'\btitle="([^"]+)"', attrs)
        title = titles.get(d.group(1)) if d else None
        title = title or (t.group(1) if t else None)
        sel = re.search(r"<option[^>]*\bselected\b[^>]*>([^<]*)</option>", body) or re.search(r"<option[^>]*>([^<]*)</option>", body)
        if title and sel:
            out.append((html.unescape(title), html.unescape(sel.group(1)).strip()))
    return out


def changes(chips: list[tuple[str, str]], seen: dict, qprefix: str) -> list[dict]:
    qre = re.compile(r"^" + re.escape(qprefix) + r"\s?(\d+)\b")
    out = []
    for title, opt in chips:
        if seen.get(title, opt if opt in INITIAL else None) == opt:
            continue
        m = qre.match(title)
        kind = "approval" if title == "Approval" else "answer" if m else None
        if kind:
            out.append({"chip": title, "kind": kind, "q": int(m.group(1)) if m else None, "option": opt})
    return out


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4) or (len(argv) == 4 and argv[3] != "--commit"):
        print(__doc__, file=sys.stderr)
        return 2
    doc, seen_path, qprefix = argv[:3]
    chips = read(open(doc, encoding="utf-8").read())
    seen = json.load(open(seen_path)) if os.path.exists(seen_path) else {}
    print(json.dumps(changes(chips, seen, qprefix)))
    if len(argv) == 4:
        tmp = seen_path + ".tmp"
        json.dump(dict(seen, **dict(chips)), open(tmp, "w"))
        os.replace(tmp, seen_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
