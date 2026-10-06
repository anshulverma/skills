# Google Doc CLI cookbook

Everything here was learned by hitting the failure first. Each gotcha below cost a round trip;
reading this costs you nothing.

`gdocs` and `google-mux docs` both print a deprecation banner pointing at `meta google.docs`. They
still work, and in one case (image sizing) the deprecated one is the only one that does the job.

## Listing comments

```bash
meta google.docs.comment list --id="$DOC" --output=json -l 200 2>/dev/null
```

Three things will bite you:

**The default limit is 10.** Without `-l 200` you get `{"truncated":true,"returned":10,...}` and
will silently miss comments. Replies count against the limit too, so a doc with 5 busy threads
blows past it.

**The response shape is inconsistent.** Sometimes a bare JSON array, sometimes
`{"truncated":...,"data":[...]}`. Handle both.

**stderr leaks into the stream.** An unrelated `E0902 ... DISTRIBUTED_TRACING settings` line can
appear ahead of the JSON even with `2>/dev/null`, and `json.load` dies on it. Parse tolerantly:

```python
import json, sys
buf = sys.stdin.read()
locs = [x for x in (buf.find('['), buf.find('{')) if x != -1]
if not locs:
    print("EMPTY RESPONSE - the CLI failed, no conclusion drawn"); sys.exit(2)
raw = json.loads(buf[min(locs):])
if isinstance(raw, dict) and raw.get('truncated'):
    print("TRUNCATED - raise -l and re-run, do NOT report this sweep"); sys.exit(2)
comments = raw['data'] if isinstance(raw, dict) else raw
```

**Assert `truncated` is false. This one has actually bitten.** A sweep that forgot `-l 200` reported
`total 44 pending 0` for weeks and read as a healthy quiet doc — the row count looked plausible
because 10 threads carry dozens of rows between them, so nothing about the output said "you are
looking at a fraction of this doc". The same doc at `-l 200` was `total 70 pending 1`, and the
pending one was a real question that had been sitting unanswered for five days. The flag is right
there in the response; check it rather than trusting the row count to look wrong.

**An empty response is not an empty doc.** Without that guard `min()` raises on an empty iterable
and the traceback reads like a parse bug. Distinguish the two states out loud: "checked, no new
comments" and "could not check" lead to opposite next moves, and the second one silently reported as
the first will have you telling the user the doc is quiet while their questions pile up.

**Skip `action` markers when picking the newest real message.** Resolving a thread appends a row with
`action: "resolve"` and empty content. Filter on `action is None` as well as non-empty content, or a
resolved thread reads as having an unanswered question and you write a full answer to the act of the
user closing it.

Retry once, then report the failure. The usual cause is an expired x509 cert — the signature is
`Failed to generate CAT` or `Client certificate has expired! path=/var/facebook/credentials/...`.
No amount of retrying fixes that; the user has to renew it. Say so rather than burning polls.

### Structure

Top-level comments have `parent_id: null`. Replies are entries in the **same** list with
`parent_id` set to the thread root — there is no nesting, so group them yourself. Useful fields:

| Field | Use |
|---|---|
| `id` | Pass to `reply` as `--comment-id` |
| `author` | The owner-only gate compares this to the invoking user |
| `content` | The comment text. `Action:` detection reads this |
| `quoted_text` | The highlighted text, or `null` for an unanchored comment |
| `ranges[0].start_index` | Character offset — orders unanchored comments against anchored ones |
| `url` | The `?disco=<id>` deep link. Put this in the companion doc |
| `resolved` | Skip resolved threads unless asked otherwise |

`reply-list` exists but takes different flags and is easy to get wrong; the replies are already in
the `list` output, so just use that.

### Deciding what needs an answer

Walk each thread oldest to newest, tracking whether the newest human message came after your last
reply:

```python
def is_marker(r):
    """A resolve/reopen event, not a message. Has an `action` set, or empty content."""
    return r.get('action') is not None or not r['content'].strip()

pending = []
for r in sorted(replies, key=lambda x: x['created_time']):
    if is_marker(r):
        continue              # not a question and not an answer
    if is_mine(r['content']):
        pending = []          # your reply clears anything before it
    else:
        pending.append(r)     # a human message after your reply is unanswered
# thread needs work if it has no replies at all, or pending is non-empty
```

Identify your own replies by the agent prefix the platform adds (`[🤖 Claude Code]`) and by
`(cont'd` for auto-split continuations. Do not match on author — the CLI posts as the invoking user,
so your replies and theirs share an author name.

**Skip the markers or you will answer resolutions.** Resolving a thread posts an empty reply with
`action: "resolve"`. It is not from you by the content test, so it lands in `pending` and the thread
reads as having an unanswered question — you then write a full answer to the act of the user closing
the thread.

The follow-up case is the one that gets missed. A question posted while you were writing the
previous answer looks answered if you only check "does any reply of mine exist".

## Replying

```bash
meta google.docs.comment reply --id="$DOC" --comment-id="$CID" --content="$(cat /tmp/reply.txt)"
```

Write the body to a file and pass it via `"$(cat ...)"`. Reply text routinely contains backticks,
`$(...)`, and quotes; inlining it invites shell expansion. Never build the argument by string
concatenation with untrusted comment text in it.

Comment bodies render as **plain text** — no markdown headings, bold, or tables. Structure with
blank lines, capitalized section labels, and indentation. Markdown syntax just shows up as literal
asterisks.

Over-long replies get silently split into a second `(cont'd 2/2)` reply. That is a symptom, not a
feature: if you are hitting it, the answer belonged in the companion doc.

Never call `resolve` or `delete`.

## Creating and updating docs

```bash
# from a ghtml file (title comes from <title> if you omit --title)
meta google.docs create --file=file:///tmp/companion.html

# replace the whole body
meta google.docs replace --id="$DOC" --file=file:///tmp/companion.html

# read it back as ghtml
meta google.docs get --id="$DOC"

# share
meta google.docs.share grant --id="$DOC" --domain --role=commenter
```

`--domain` is a **boolean flag**, not `--domain=meta.com`. Passing a value errors.

`meta google.docs create` needs `--title` unless the HTML has a `<title>` tag.

Heading anchors for deep links come back from `get` as `data-heading-id`:

```bash
meta google.docs get --id="$DOC" 2>/dev/null | grep -oE '<h[0-9] data-heading-id="[^"]*">[^<]*'
```

Link a section as `https://docs.google.com/document/d/<id>/edit#heading=<data-heading-id>`.

## Images

This is the fiddliest part. Three separate traps.

**1. Upload for a gsuite-embeddable URL.**

```bash
google-mux docs upload-image /tmp/fig.png    # -> https://mmg.whatsapp.net/...
```

Pixelcloud links do **not** embed in Google Docs. Use this, not `meta pixelcloud.image upload`.

**2. Insert with an explicit size.**

```bash
google-mux docs content insert-image "$DOC" "$IMAGE_URL" \
  --after-text "Figure 01." --width 468 --height 274
```

`meta google.docs.insert image` has **no `--width`/`--height`**. Without sizing, a 2380px-wide
figure renders at native size and blows out the page. 468pt is the text width of a default
letter-size doc; compute height as `468 * (px_h / px_w)` to keep the aspect ratio.

**3. Give the image a paragraph to land in.**

`--after-text` inserts after the paragraph containing that text. If the next element is a table or
the document end, the API rejects it:

> The insertion index must be inside the bounds of an existing paragraph.

Put an empty paragraph after every caption in the ghtml, and anchor on the caption:

```html
<p><i>Figure 01. What the diagram shows.</i></p>
<p>&nbsp;</p>
```

Use zero-padded, unique anchors (`Figure 01.` … `Figure 10.`) so `Figure 1.` cannot also match
`Figure 10.`. With a unique anchor per image, insertion order does not matter. If you must reuse
one anchor for several images, insert in reverse — each insert pushes earlier ones down.

## Rendering figures

There is no matplotlib in the devserver python, and no `PIL`, `cairosvg`, `rsvg-convert`,
`inkscape`, `convert`, or headless chrome either. Render through a Bento kernel:

```bash
bento console --kernel bento_kernel_ads_generative_retrieval --file /tmp/figs.py 2>&1 \
  | grep -Ev "^I[0-9]|^W[0-9]|Debugger|Bento kernel|WARNING:|All packages verified"
```

The script must `matplotlib.use("Agg")` before importing pyplot, and `savefig` to `/tmp`.

## Research surfaces

- fbsource code: `mcp__plugin_meta_mux__search_files`, or the `meta_codesearch:code-search` agent.
  **Never** Grep/Glob/`rg`/`find` — recursive traversal of the virtual filesystem times out.
- Internal URLs (wiki, task, diff, paste, Workplace): `mcp__plugin_meta_mux__knowledge_load`.
- External web pages: usually blocked by input filtering. Do not keep retrying.
- arXiv papers, no internet flag needed:
  ```bash
  meta corpus.search query --query='<topic>' --limit 10        # search, returns arxiv URLs
  meta search.paper search --query='<topic>' --limit 10        # internal mirror
  meta search.paper load --arxiv-id 2607.07508 --no-truncate   # full text
  ```
  The mirror is incomplete and skews recent — a miss means "not indexed", not "does not exist".
  `--max-sections 0` is needed for the full body; the default truncates at 15 sections.

## Risk annotations

`meta` commands carry a server-side risk annotation. Before a mutating call you have not made
before:

```bash
meta metacli.command annotations --command "google.docs.share grant" -o json
```

`control: AUTONOMOUS` is fine to proceed with. `CONFIRM` or `2FA` means ask the user first.
