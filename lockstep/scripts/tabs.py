#!/usr/bin/env python3
"""Tabs layout: one private lockstep doc per run, one tab per run doc. Comment-safe tab writes.

Usage:
  tabs.py ensure RUN KEY --title T --tab-title N --kind K [--parent KEY] [--qprefix P]   (prints the tab id)
  tabs.py private RUN                     (exit 0 private, 2 not private)
  tabs.py get RUN KEY                     (prints {path, bytes, open_quotes, open_image_threads})
  tabs.py apply RUN KEY --body BODY.html [--ours] [--allow-reset OBJ ...]   (generated tabs)
  tabs.py apply RUN KEY --authored [--allow-reset OBJ ...]                  (authored tabs: applies docs/KEY/live.html)
  tabs.py size RUN                        (exit 4 when a tab is over 300 KB or all tabs over 450 KB)
apply exits 0 applied or already current, 3 nothing applied and a pass held, 5 a frame reset needs replies, 2 refused.
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time

import state

OURS_KEYS = ("tracker", "events")
GATED_KINDS = ("proposal", "spec", "task")
NO_QUESTION_KINDS = ("study", "takeaways")  # no numbered questions: never a qprefix
TAB_MAX, DOC_MAX = 300_000, 450_000
ASPECT_TOL = 0.10
RETRY_SLEEP = float(os.environ.get("LOCKSTEP_RETRY_SLEEP", "5"))

ASIDE = re.compile(r"<aside hidden>(.*?)</aside>", re.S)
FILE_IMG = re.compile(r'<img\b[^>]*\bsrc="file://([^"]+)"[^>]*>')
LIVE_IMG = re.compile(r'<img\b[^>]*\bdata-object-id="([^"]+)"[^>]*>')
TABLE = re.compile(r"<table\b.*?</table>", re.S)
ROW = re.compile(r"<tr\b.*?</tr>", re.S)
CELL = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.S)
BLOCK = re.compile(r"<(p|h[1-6]|li)\b[^>]*>.*?</\1>", re.S)
TRANSIENT = re.compile(r"php_oom|out of memory|internal error|backend error|unavailable|timed? ?out|deadline|"
                       r"\b50[0-4]\b|problem retrieving the image", re.I)


class Refused(Exception):
    pass


# ---------- meta ----------

def _meta(*args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(["meta", *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)


def _ok(*args: str) -> str:
    p = _meta(*args)
    if p.returncode:
        raise RuntimeError(f"meta {' '.join(args[:2])} failed ({p.returncode}): {(p.stderr or p.stdout).strip()[-400:]}")
    return p.stdout


def _json_in(out: str):
    dec = json.JSONDecoder()
    for i, ch in enumerate(out):  # skip "Poll hint" and other noise around the JSON
        if ch in "[{":
            try:
                return dec.raw_decode(out[i:])[0]
            except ValueError:
                continue
    raise ValueError(f"no JSON in meta output: {out.strip()[:200]!r}")


# ---------- run state ----------

def _load(run: str) -> dict:
    p = state.load(run)
    if p.get("layout") != "tabs":
        raise Refused("pipeline.json layout is not \"tabs\"")
    if not p.get("tracker_doc"):
        raise Refused("tracker_doc is not set")
    return p


def _tab(p: dict, key: str) -> str:
    d = p.get("docs", {}).get(key) or {}
    tab = d.get("tab") or (p.get("tracker_tab") if key == "tracker" else None)
    if not tab:
        raise Refused(f"docs.{key}.tab is not set")
    return tab


def _stage(run: str, key: str) -> str:
    d = os.path.join("/tmp", f"lockstep-{os.path.basename(os.path.abspath(run))}", key)
    os.makedirs(d, exist_ok=True)
    return d


def _workdir(run: str, key: str) -> str:
    d = os.path.join(run, "docs", key)
    os.makedirs(d, exist_ok=True)
    return d


def private(doc: str) -> bool:
    perms = _json_in(_ok("google.docs.share", "list", f"--id={doc}", "--output=json"))
    # the DOCS.md predicate: non-empty and every entry an owner; any other shape fails closed
    return isinstance(perms, list) and bool(perms) and all(isinstance(e, dict) and e.get("role") == "owner" for e in perms)


def _require_private(doc: str) -> None:
    if not private(doc):
        raise Refused(f"doc {doc} is not private")


# ---------- parsing ----------

def _attrs(tag: str) -> dict:
    return {k: html.unescape(v) for k, v in re.findall(r'([\w-]+)="([^"]*)"', tag)}


def _text(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", ASIDE.sub("", s))).split())


def threads(live: str, tab: str) -> list[dict]:
    """Open, still-anchored comment threads on this tab: {id, quote, start, end}. Orphans carry no ranges."""
    out = []
    for m in ASIDE.finditer(live):
        root = re.match(r"\s*<div\b([^>]*)>", m.group(1))
        a = _attrs(root.group(1)) if root else {}
        if a.get("data-status") == "OPEN" and a.get("data-ranges") and a.get("data-tab-id") == tab \
                and a.get("data-orphaned") != "true":
            out.append({"id": a.get("data-id"), "quote": a.get("data-quote", ""), "start": m.start(), "end": m.end()})
    return out


def image_threads(live: str, tab: str) -> dict[str, list[str]]:
    """{object_id: [thread ids]}: a comment on an image has no quote and its aside follows the image's paragraph."""
    imgs = list(LIVE_IMG.finditer(live))
    out: dict[str, list[str]] = {}
    for t in threads(live, tab):
        if t["quote"].strip():
            continue
        prev = [m for m in imgs if m.end() <= t["start"]]
        if prev and re.fullmatch(r"(\s|</p>|<aside hidden>.*?</aside>)*", live[prev[-1].end():t["start"]], re.S):
            out.setdefault(prev[-1].group(1), []).append(t["id"])
    return out


def _png_size(path: str) -> tuple[int, int]:
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", head[16:24])


def _sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _dims(tag: str) -> tuple[float, float]:
    a = _attrs(tag)
    return float(a["width"]), float(a["height"])


def fig_key(run: str | None, png: str) -> str:
    """figs.json key: the image path relative to the run dir, or the absolute path outside it."""
    a = os.path.abspath(png)
    if not run:
        return a
    rel = os.path.relpath(a, os.path.abspath(run))
    return a if rel.split(os.sep)[0] == os.pardir else rel


def _first(row: str) -> str:
    c = CELL.search(row)
    return _text(c.group(1)) if c else ""


# ---------- library ----------

def build_from(body: str, live: str, figs: dict, tab: str, allow_reset=(), hold: bool = True,
               run: str | None = None) -> dict:
    """BODY with (a) live image tags kept and swaps queued, (b) live blocks held where an open quote would vanish.
    Returns {html, swaps: [{name, fig, png, object_id, w, h, preserve}], new_images: [png], blocked: {oid: [ids]},
    held, unplaced}: unplaced quotes have no counterpart block in BODY, so the structure pass must hold."""
    tags = {m.group(1): m.group(0) for m in LIVE_IMG.finditer(live)}
    img_threads = image_threads(live, tab)
    swaps, new, blocked = [], [], {}

    def keep(m):
        png = m.group(1)
        f = figs.get(fig_key(run, png)) or {}
        oid = f.get("object_id")
        if oid not in tags:
            new.append(png)
            return m.group(0)  # a new figure: the apply uploads it
        w, h = _dims(tags[oid])
        if _sha(png) != f.get("sha256"):
            W, H = _png_size(png)
            preserve = abs(W / H - w / h) <= ASPECT_TOL * (w / h)
            if not preserve and img_threads.get(oid) and oid not in allow_reset:
                blocked[oid] = img_threads[oid]
            else:
                swaps.append({"name": os.path.basename(png), "fig": fig_key(run, png), "png": png, "object_id": oid,
                              "w": w, "h": h, "preserve": preserve})
        return tags[oid]

    out = FILE_IMG.sub(keep, body)
    held, unplaced = [], []
    if hold:
        out, held, unplaced = _hold(out, live, [t for t in threads(live, tab) if t["quote"].strip()])
    return {"html": out, "swaps": swaps, "new_images": new, "blocked": blocked, "held": held, "unplaced": unplaced}


def _anchor(live: str, pos: int) -> re.Match | None:
    """The table or block a comment's aside follows: asides stack after the anchored paragraph, or after the
    whole table for a comment inside a cell (scratch doc and run doc readback)."""
    while live[:pos].rstrip().endswith("</aside>"):
        pos = live.rfind("<aside hidden>", 0, pos)
    end = len(live[:pos].rstrip())
    hits = [m for rx in (TABLE, BLOCK) for m in rx.finditer(live) if m.end() == end]
    return hits[0] if hits else None


def _blocks(s: str) -> list[tuple[tuple[str, int], re.Match]]:
    """Blocks outside tables and asides, each keyed by (text of the nearest preceding heading, index under it)."""
    skip = [m.span() for rx in (TABLE, ASIDE) for m in rx.finditer(s)]
    out, head, i = [], "", 0
    for m in BLOCK.finditer(s):
        if any(a <= m.start() < b for a, b in skip):
            continue
        out.append(((head, i), m))
        head, i = (_text(m.group(0)), 0) if m.group(1)[0] == "h" else (head, i + 1)
    return out


def _section(s: str, pos: int) -> str:
    """Text of the nearest h1/h2 before pos: the unit (a study, a tab part) a block belongs to."""
    heads = [m for m in BLOCK.finditer(s, 0, pos) if m.group(1) in ("h1", "h2")]
    return _text(heads[-1].group(0)) if heads else ""


def _counterpart(body: str, live: str, src: re.Match) -> re.Match | None:
    """The BODY block that replaces the commented live block: same tag and same h1/h2 section, then the longest
    shared leading text (a label like "Status: "), then the nearest position. Position alone is not enough: a
    block inserted above shifts every index."""
    def peers(s, sec):
        return [bm for _, bm in _blocks(s) if bm.group(1) == src.group(1) and _section(s, bm.start()) == sec]

    sec = _section(live, src.start())
    at = next((k for k, bm in enumerate(peers(live, sec)) if bm.start() == src.start()), 0)
    txt = _text(src.group(0))
    cands = list(enumerate(peers(body, sec)))
    if not cands:
        return None
    return max(cands, key=lambda kb: (len(os.path.commonprefix([txt, _text(kb[1].group(0))])), -abs(kb[0] - at)))[1]


def _hold(body: str, live: str, open_threads: list[dict]) -> tuple[str, list[str], list[str]]:
    held, unplaced = [], []
    for t in open_threads:
        q = " ".join(t["quote"].split())
        m = _anchor(live, t["start"])
        el = m.group(0) if m else None
        tables = [el] if el and el.startswith("<table") else TABLE.findall(live)
        hit = next(((tb, r) for tb in tables for r in ROW.findall(tb) if q in _text(r)), None)
        if hit:
            table, row = hit
            body_rows = {_first(r): r for r in ROW.findall(body)}
            mine = body_rows.get(_first(row))
            if mine is not None and q in _text(mine):
                continue
            if mine is not None:
                body = body.replace(mine, row, 1)
            else:  # the row was removed: put it back after its live predecessor
                rows = ROW.findall(table)
                i = rows.index(row)
                prev = body_rows.get(_first(rows[i - 1])) if i else None
                if not prev:
                    continue  # nowhere to put it; the dry-run refuses the orphaning pass
                body = body.replace(prev, prev + "\n" + row, 1)
        else:
            lives = _blocks(live)
            src = next((km for km in lives if m and km[1].start() == m.start() and q in _text(el)), None) or \
                next((km for km in lives if q in _text(km[1].group(0))), None)
            if not src:
                continue
            mine = _counterpart(body, live, src[1])
            if mine is not None and q in _text(mine.group(0)):
                continue
            if mine is None:
                sec = _section(live, src[1].start())
                if any(q in _text(bm.group(0)) for _, bm in _blocks(body) if _section(body, bm.start()) == sec):
                    continue  # the block was rewritten but the commented text survives in its section
                unplaced.append(t["quote"])  # no counterpart: the structure pass would raze it, so it holds
                continue
            body = body[:mine.start()] + src[1].group(0) + body[mine.end():]
        held.append(t["quote"])
    return body, held, unplaced


def pass1(live: str, new: str) -> str:
    """Live content with each live table row replaced by the same-key row of NEW: cell edits only, no structure."""
    def key(t):
        rows = ROW.findall(t)
        return _text(rows[0]) if rows else ""

    rows = {}
    for t in TABLE.findall(new):
        for r in ROW.findall(t)[1:]:
            rows.setdefault((key(t), _first(r)), r)

    def table(m):  # the header row stays live: Docs reads it back as <th>, the render writes <td>
        k, header = key(m.group(0)), ROW.search(m.group(0))
        return ROW.sub(lambda r: r.group(0) if r.start() == header.start() else rows.get((k, _first(r.group(0))),
                                                                                       r.group(0)), m.group(0))
    return TABLE.sub(table, live)


def pad(png: str, w: float, h: float, out: str) -> str:
    """Pad PNG to the live frame's aspect with its own background colour, so --preserve-frame never crops it."""
    from PIL import Image
    im = Image.open(png).convert("RGB")
    W, H = im.size
    size = (round(H * w / h), H) if W / H < w / h else (W, round(W * h / w))
    canvas = Image.new("RGB", size, im.getpixel((0, 0)))
    canvas.paste(im, ((size[0] - W) // 2, (size[1] - H) // 2))
    canvas.save(out)
    return out


# ---------- commands ----------

def ensure(run: str, key: str, title: str, tab_title: str, kind: str, parent: str | None, qprefix: str | None) -> str:
    p = _load(run)
    doc = p["tracker_doc"]
    docs = p.setdefault("docs", {})
    d = docs.get(key) or {}
    if kind in NO_QUESTION_KINDS:
        qprefix = None
    elif kind in GATED_KINDS and not (qprefix or d.get("qprefix")):
        raise Refused(f"--kind {kind} is gated and needs --qprefix")
    tabs = _json_in(_ok("google.docs.tab", "list", f"--id={doc}", "--depth=0", "--columns=all", "--output=json"))
    if d.get("tab") and not d.get("archived") and any(t.get("tabId") == d["tab"] for t in tabs):
        return d["tab"]
    ptab = _tab(p, parent) if parent else ""
    # never adopt a tab another key records (archived ones included), nor this key's own archived tab
    owned = {v.get("tab") for k, v in docs.items() if isinstance(v, dict) and (k != key or v.get("archived"))}
    owned |= {p.get(f) for f, k in (("tracker_tab", "tracker"), ("tracker_events_tab", "events")) if k != key}
    tab = next(
        (t["tabId"] for t in tabs if t.get("title") == tab_title and (t.get("parent_tabId") or "") == ptab
         and t.get("tabId") not in owned), None)
    if not tab:  # adopting first means a crash between add and save never leaves a duplicate tab (2FA to delete)
        args = ["google.docs.tab", "add", f"--id={doc}", f"--title={tab_title}", "--output=json"]
        got = _json_in(_ok(*args, *([f"--parent-tab-id={ptab}"] if ptab else [])))
        got = got[0] if isinstance(got, list) and got else got
        tab = next((got.get(k) for k in ("tabId", "tab_id", "id") if isinstance(got, dict) and got.get(k)), None)
        if not tab:
            raise RuntimeError(f"tab add returned no tab id: {got!r}")
    d = {k: v for k, v in d.items() if k != "archived" and not (k == "qprefix" and kind in NO_QUESTION_KINDS)}
    docs[key] = {**d, "id": doc, "tab": tab, "parent": parent, "title": title, "tab_title": tab_title, "kind": kind,
                 **({"qprefix": qprefix} if qprefix else {}),
                 "status": d.get("status") or ("drafting" if kind in GATED_KINDS else "reference")}
    if key == "events":
        p["tracker_events_tab"] = tab
    state.save(run, p)
    state.append_event(run, "tab_created", f"tab {tab_title} ({tab})", doc=key, tab=tab)
    return tab


def _get(run: str, p: dict, key: str) -> tuple[str, str]:
    """Fetch one tab to /tmp and copy live.html(+.base) to docs/<key>/. Returns (live text, staged path)."""
    dest = os.path.join(_stage(run, key), "live.html")
    _ok("google.docs", "get", f"--id={p['tracker_doc']}", f"--tab-id={_tab(p, key)}", "--output=ghtml",
        f"--dest=file://{dest}")
    wd = _workdir(run, key)
    for suffix in ("", ".base"):
        shutil.copyfile(dest + suffix, os.path.join(wd, "live.html" + suffix))
    return open(dest, encoding="utf-8").read(), dest


def get(run: str, key: str) -> dict:
    p = _load(run)
    _require_private(p["tracker_doc"])
    live, _ = _get(run, p, key)
    tab = _tab(p, key)
    path = os.path.join(_workdir(run, key), "live.html")
    return {"path": path, "bytes": os.path.getsize(path),
            "open_quotes": [t["quote"] for t in threads(live, tab) if t["quote"].strip()],
            "open_image_threads": image_threads(live, tab)}


def _held_reason(out: str) -> str | None:
    if "would orphan" in out:
        return "orphans comments"
    if "would conflict" in out:
        return "conflict"
    return None


def _apply_pass(p: dict, key: str, content: str, base: str, stage: str, ours: bool) -> str:
    """One dry-run then one real apply. Returns applied | nochange | held: <reason>. Never forces."""
    src = os.path.join(stage, "from.html")
    args = ["google.docs", "apply", f"--id={p['tracker_doc']}", f"--tab-id={_tab(p, key)}", f"--from=file://{src}",
            f"--base=file://{base}", *(["--conflict-resolution=ours"] if ours else [])]
    for dry in (True, False):
        for attempt in range(3):
            open(src, "w", encoding="utf-8").write(content)  # a real apply rewrites --from with the committed doc
            r = _meta(*args, *(["--dry-run"] if dry else []))
            out = r.stdout + r.stderr
            if r.returncode == 0 or (not dry and "✓ Applied" in out):
                break
            if (why := _held_reason(out)):
                return f"held: {why}"
            if not TRANSIENT.search(out) or attempt == 2:
                raise RuntimeError(f"apply{' --dry-run' if dry else ''} failed ({r.returncode}): {out.strip()[-400:]}")
            time.sleep(RETRY_SLEEP * (attempt + 1))
        if dry and "No changes" in out:
            return "nochange"
    return "applied"


def _swap(p: dict, key: str, s: dict, stage: str) -> str:
    """replace-image on this tab; returns the (possibly new) object id."""
    png = pad(s["png"], s["w"], s["h"], os.path.join(stage, "framed-" + s["name"])) if s["preserve"] else s["png"]
    args = ["google.docs", "replace-image", f"--id={p['tracker_doc']}", f"--tab-id={_tab(p, key)}",
            f"--image-id={s['object_id']}", f"--new-image=file://{png}", "--output=json",
            *(["--preserve-frame"] if s["preserve"] else [])]
    try:
        out = _ok(*args)
    except RuntimeError:
        time.sleep(RETRY_SLEEP)
        out = _ok(*args)  # Google's transient 400 "problem retrieving the image"
    return _json_in(out).get("imageObjectId") or s["object_id"]


def _finish(run: str, p: dict, key: str, r: dict, before: str, applied: bool, stage: str, figs: dict) -> None:
    """Run the queued swaps, then record object ids, frames and hashes in figs.json."""
    figs_path = os.path.join(_workdir(run, key), "figs.json")
    for s in r["swaps"]:
        oid = _swap(p, key, s, stage)
        figs[s["fig"]] = {**figs.get(s["fig"], {}), "object_id": oid, "sha256": _sha(s["png"])}
        state.atomic_write_json(figs_path, figs)  # a later swap failing must not lose this object id
        if not s["preserve"]:
            state.append_event(run, "figure_frame_reset", f"figure {s['fig']} re-inserted with a fresh frame",
                               doc=key, old=s["object_id"], new=oid)
    if not (r["swaps"] or (applied and r["new_images"])):
        return
    live, _ = _get(run, p, key)
    old = set(LIVE_IMG.findall(before))
    added = [o for o in LIVE_IMG.findall(live) if o not in old and o not in {f.get("object_id") for f in figs.values()}]
    if applied and r["new_images"]:
        if len(added) == len(r["new_images"]):
            for png, oid in zip(r["new_images"], added):
                figs[fig_key(run, png)] = {"object_id": oid, "sha256": _sha(png)}
        else:
            print(f"{key}: {len(r['new_images'])} images sent, {len(added)} new on the tab; figs.json not updated "
                  "for them", file=sys.stderr)
    tags = {m.group(1): m.group(0) for m in LIVE_IMG.finditer(live)}
    for f in figs.values():
        if f.get("object_id") in tags:
            f["w"], f["h"] = _dims(tags[f["object_id"]])
    state.atomic_write_json(figs_path, figs)


def _figs(run: str, key: str, body: str) -> dict:
    """figs.json, with each old basename key moved to the one BODY image of that name; dropped when two BODY images
    share the name (they re-upload). Kept as is when no BODY image has it."""
    path = os.path.join(run, "docs", key, "figs.json")
    figs = state.read_json(path) if os.path.exists(path) else {}
    pngs = {fig_key(run, m) for m in FILE_IMG.findall(body)}
    out = {k: v for k, v in figs.items() if os.sep in k or k in pngs}
    for name, v in figs.items():
        hits = [k for k in pngs if os.path.basename(k) == name]
        if name in out or len(hits) > 1:
            continue
        if not hits or hits[0] not in out:
            out[hits[0] if hits else name] = v
    return out


def apply_generated(run: str, key: str, body_path: str, ours: bool, allow_reset=()) -> int:
    if ours and key not in OURS_KEYS:
        raise Refused(f"--ours is only for {', '.join(OURS_KEYS)}, not {key}")
    p = _load(run)
    tab = _tab(p, key)
    _require_private(p["tracker_doc"])
    live, dest = _get(run, p, key)
    body = open(body_path, encoding="utf-8").read()
    figs = _figs(run, key, body)
    r = build_from(body, live, figs, tab, allow_reset, run=run)
    if r["blocked"]:
        print(json.dumps({"frame_reset_needs_replies": r["blocked"]}))
        return 5
    if r["held"]:
        state.append_event(run, "apply_held", f"{len(r['held'])} blocks kept live for open comments", doc=key,
                           quotes=r["held"])
    stage, before = _stage(run, key), live
    results = []
    for name, build in (("cells", lambda lv: pass1(lv, r["html"])), ("structure", lambda lv: r["html"])):
        content = build(live)
        if content == live:
            continue
        res = "held: no counterpart for an open comment" if name == "structure" and r["unplaced"] else \
            _apply_pass(p, key, content, dest + ".base", stage, ours)
        results.append(res)
        if res.startswith("held"):
            state.append_event(run, "apply_held", f"{name} pass held: {res[6:]}", doc=key, apply_pass=name)
        elif res == "applied":
            live, dest = _get(run, p, key)  # the next pass merges against the committed doc
    applied = "applied" in results
    print(json.dumps({"key": key, "passes": results, "held": r["held"], "swaps": len(r["swaps"])}))
    # swaps change pixels only, so they run even when both text passes are held
    _finish(run, p, key, r, before, applied, stage, figs)
    return 3 if not applied and any(x.startswith("held") for x in results) else 0


def apply_authored(run: str, key: str, allow_reset=()) -> int:
    p = _load(run)
    tab = _tab(p, key)
    _require_private(p["tracker_doc"])
    wd = _workdir(run, key)
    edited, base = os.path.join(wd, "live.html"), os.path.join(wd, "live.html.base")
    if not os.path.exists(base):
        raise Refused(f"no {base}: run tabs.py get {key} first")
    base_text, body = open(base, encoding="utf-8").read(), open(edited, encoding="utf-8").read()
    figs = _figs(run, key, body)
    r = build_from(body, base_text, figs, tab, allow_reset, hold=False, run=run)
    if r["blocked"]:
        print(json.dumps({"frame_reset_needs_replies": r["blocked"]}))
        return 5
    stage = _stage(run, key)
    staged_base = shutil.copyfile(base, os.path.join(stage, "authored.base"))  # meta rewrites files it applies
    res = _apply_pass(p, key, r["html"], staged_base, stage, ours=False)
    print(json.dumps({"key": key, "passes": [res], "swaps": len(r["swaps"])}))
    if res.startswith("held"):
        state.append_event(run, "apply_held", f"authored apply held: {res[6:]}", doc=key)
        return 3
    _finish(run, p, key, r, base_text, res == "applied", stage, figs)
    return 0


def size(run: str) -> tuple[int, dict]:
    p = _load(run)
    sizes = {}
    for key, d in p.get("docs", {}).items():
        path = os.path.join(run, "docs", key, "live.html")
        if isinstance(d, dict) and d.get("tab") and os.path.exists(path):
            sizes[key] = os.path.getsize(path)
    if "tracker" not in sizes and os.path.exists(os.path.join(run, "docs", "tracker", "live.html")):
        sizes["tracker"] = os.path.getsize(os.path.join(run, "docs", "tracker", "live.html"))
    total = sum(sizes.values())
    over = total > DOC_MAX or any(v > TAB_MAX for v in sizes.values())
    return (4 if over else 0), {"tabs": sizes, "total": total}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(usage=__doc__)
    ap.add_argument("cmd", choices=("ensure", "private", "get", "apply", "size"))
    ap.add_argument("run")
    ap.add_argument("key", nargs="?")
    ap.add_argument("--title")
    ap.add_argument("--tab-title")
    ap.add_argument("--kind")
    ap.add_argument("--parent")
    ap.add_argument("--qprefix")
    ap.add_argument("--body")
    ap.add_argument("--ours", action="store_true")
    ap.add_argument("--authored", action="store_true")
    ap.add_argument("--allow-reset", action="append", default=[])
    a = ap.parse_args(argv)
    try:
        if a.cmd in ("ensure", "get", "apply") and not a.key:
            raise Refused(f"{a.cmd} needs KEY")
        if a.cmd == "ensure":
            if not (a.title and a.tab_title and a.kind):
                raise Refused("ensure needs --title, --tab-title and --kind")
            print(ensure(a.run, a.key, a.title, a.tab_title, a.kind, a.parent, a.qprefix))
        elif a.cmd == "private":
            if not private(_load(a.run)["tracker_doc"]):
                print("not private", file=sys.stderr)
                return 2
        elif a.cmd == "get":
            print(json.dumps(get(a.run, a.key), ensure_ascii=False))
        elif a.cmd == "apply":
            if a.authored == bool(a.body) or (a.authored and a.ours):
                raise Refused("apply takes exactly one of --body or --authored; --ours never goes with --authored")
            if a.authored:
                return apply_authored(a.run, a.key, a.allow_reset)
            return apply_generated(a.run, a.key, a.body, a.ours, a.allow_reset)
        else:
            rc, out = size(a.run)
            print(json.dumps(out))
            return rc
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    except (RuntimeError, ValueError, OSError, KeyError, subprocess.TimeoutExpired) as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
