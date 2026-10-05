# Visuals and links

Read this when redrafting, to pick the visual each section needs and to write it in the
target format. Every visual replaces prose that would otherwise describe the same thing;
none is decorative.

## Which visual

| The content is | Use |
|---|---|
| A process, request path, retry or decision flow, or state machine | Mermaid flowchart or state diagram |
| Components exchanging messages over time | Mermaid sequence diagram |
| A trend, or numbers compared across categories | A chart. When the data lives in a Daiquery query, Deltoid experiment or Metric 360 metric, embed it live; otherwise render a PNG following the `dataviz` skill (REQUIRED SUB-SKILL for any chart). |
| Three to six headline numbers | A small "at a glance" table near the top |
| A risk, a caveat, or a decision someone must make | A tinted callout |
| Code the reader has to see | A CodeHub embed, commit-pinned |

A chart's title states what its data shows and nothing more: if one point breaks the trend, the title does not claim the trend. Do not use a categorical axis for numeric ranges with gaps between them; it hides the gaps. A chart that only repeats a table next to it adds nothing, so keep one of the two.

A two-page doc usually carries one to three visuals. Give each a caption, `Figure N. What it shows.`, and refer to it from the text ("Figure 1 shows the retry path"). Put a source link directly under any chart or data table.

## Links

Every reference a reader could want to open is a link with descriptive text:

| Reference | Link target |
|---|---|
| Diff, task, SEV, paste (`D…`, `T…`, `S…`, `P…`) | Google Docs auto-links the bare ID; in markdown use `https://www.internalfb.com/diff/D…`, `/T…`, `/sevmanager/view/<n>`, `/phabricator/paste/view/P…` |
| `file.py:123` | CodeHub, commit-pinned: `https://www.internalfb.com/code/fbsource/[<rev>]/<repo-relative path>?lines=123`, with `<rev>` from `sl log -r . -T '{node}'` |
| MAST job | `https://www.internalfb.com/mast/job/<job name>` |
| Docs, dashboards, queries | The URL the original gives |

Link only to a target the original gives or that a lookup confirmed (the file and line exist at that revision). Never guess a line range for code the original does not locate, and never link a local path such as `/home/...` or `/tmp/...`, which no other reader can open.

In text meant to be pasted somewhere else (a terminal, a chat message), write the bare URL instead, because link text hides the address.

## Local markdown

- Mermaid: a fenced block tagged `mermaid`.
- Image: `![Figure 1. Retry path](figure-1.png)`, with the PNG saved next to the version file.
- Charts are PNG, because Google Docs does not embed SVG. The system Python has no matplotlib; make one reusable environment: `python3 -m venv ~/.cache/humanize-venv && ~/.cache/humanize-venv/bin/pip install matplotlib`, then render with `~/.cache/humanize-venv/bin/python`.
- Link: `[descriptive text](https://...)`.

## Google Docs (ghtml)

Run `meta google.docs ghtml` for the full reference. The pieces this skill uses:

```html
<p style="text-align:center"><embed type="mermaid" width="600" alt="Retry path">flowchart LR; A[score call] --> B{shed?}</embed></p>
<p style="text-align:center"><i>Figure 1. What happens to a shed request.</i></p>

<aside style="background-color:#FEF7E0"><b>Decision needed:</b> who owns the JustKnob.</aside>

<p style="text-align:center"><img src="file:///tmp/humanize/<doc>/figure-2.png" alt="Score by pass"></p>

<embed src="https://www.internalfb.com/code/fbsource/[<rev>]/fbcode/path/file.py?lines=10-30">
```

- Callout tints: info `#E8F0FE`, success `#E6F4EA`, warning `#FEF7E0`, error `#FCE8E6`.
- A `file:///` image is uploaded automatically on a file-based `apply`. Keep each image or embed in its own `<p>`.
- After applying, read the doc back (`meta google.docs get --id=<id>`) and confirm every diagram and image rendered. If an image is missing, upload it with `google-mux docs upload-image <png>` and insert it with `meta google.docs insert image --id <doc> --image <url>`.
