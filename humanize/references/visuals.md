# Visuals and links

Read this when redrafting, to pick the visual each section needs and to write it in the
target format. Every visual replaces prose that would otherwise describe the same thing;
none is decorative.

## Which visual

| The content is | Use |
|---|---|
| A process, request path or architecture | A card-style Graphviz infographic (`card-diagram.dot`) |
| A rule that changes a value over time (a controller, a backoff, a retry budget) | A chart of the value over time with each rule annotated where it fires, labelled as an illustration |
| A decision with a few outcomes | A small table, or a three-to-five box Graphviz flow |
| Components exchanging messages over time | Mermaid sequence diagram |
| A trend, or numbers compared across categories | A chart. When the data lives in a Daiquery query, Deltoid experiment or Metric 360 metric, embed it live; otherwise render a PNG following the `dataviz` skill (REQUIRED SUB-SKILL for any chart). |
| Three to six headline numbers | A small "at a glance" table near the top |
| Two to four headline numbers on a slide | Big-number cards, written as a `cards` block (see `slides.md`) |
| A risk, a caveat, or a decision someone must make | A tinted callout |
| Code the reader has to see | A CodeHub embed, commit-pinned |

**A figure shows what the text right above it says.** When the paragraph walks a flow, the figure draws that flow: the same steps, with the same names, in the same order, including the way back. Anything the text places on the path (a limit, a check) sits where the text puts it. Write or revise the paragraph and its figure together, and check one against the other.

**Diagrams carry shape, not sentences.** Label each element in place: a box label is at most about 4 words and an arrow label at most 3. Keep a diagram to about 7 boxes. A box that needs a sentence to be understood belongs in the prose next to the diagram, not inside it.

**Make it look designed, not default.** Mermaid's default styling renders flat grey boxes, so for any flow or architecture figure render a styled PNG with Graphviz (installed at `/usr/bin/dot`), starting from `card-diagram.dot` in this directory: rounded cards with a coloured header per stage, tinted badges inside each card, and a legend. Use colour to encode one thing the reader needs (owner, or status such as proposed / landed / unpublished), take the colours from the `dataviz` reference palette, and state the encoding in the legend. Look at the rendered PNG before using it, and fix any overlap or cramped label. Keep Mermaid for quick sketches and for diagrams the reader should be able to edit in the doc.

**Figure slop** is the visual form of AI prose, and a figure with any of these gets redrawn:
- numbered markers (①, ②) decoded in the caption, which make the reader jump between figure and caption; label in place instead;
- filler badges and subtitles that add no fact ("non-production, 2 tiers" under a box title);
- a legend for an encoding the reader does not need;
- an annotation that makes another section's point;
- axis labels or titles carrying process notes ("bins the RCA reports");
- a caption that repeats the values printed in the chart or the paragraph, or that decodes the figure instead of saying what it shows;
- decoration: shadows, gradients, icons, colour that encodes nothing.

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

Link only to a target the original gives, one built from the patterns above for an ID the original names, or one a lookup confirmed (the file and line exist at that revision). Never guess a line range for code the original does not locate, and never link a local path such as `/home/...` or `/tmp/...`, which no other reader can open.

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

- Mermaid source goes in unescaped (`-->` stays as is), with each newline written as `&#10;` and no `<br/>` inside labels. HTML-escaped source or `<br/>` labels land in the doc as a paragraph of plain text instead of a diagram. Confirm on readback that each diagram came back as `<embed type="mermaid" src="https://draw.internalmeta.com/...">`.
- Title and TL;DR: `<p data-style="TITLE">Plain-words title</p>`, then `<aside style="background-color:#E8F0FE"><b>TL;DR</b><ul><li>problem</li><li>fix</li><li>guarantee</li></ul></aside>`. Also set the doc's own title with `meta google.docs update --id=<id> --title="..."`.
- Callout tints: info `#E8F0FE`, success `#E6F4EA`, warning `#FEF7E0`, error `#FCE8E6`.
- A `file:///` image is uploaded automatically on a file-based `apply`. Keep each image or embed in its own `<p>`.
- After applying, read the doc back (`meta google.docs get --id=<id>`) and confirm every diagram and image rendered. If an image is missing, upload it with `google-mux docs upload-image <png>` and insert it with `meta google.docs insert image --id <doc> --image <url>`.
