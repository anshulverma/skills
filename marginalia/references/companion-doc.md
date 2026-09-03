# Building the companion doc

The companion doc is where a long answer goes so the comment thread can stay short. It is also the
archive: months later the thread is a stub, and this is the only record of what was asked and what
the answer actually was. Write it for someone who was not in the conversation.

## Structure

```html
<html>
<head><title>&lt;Source doc title&gt; — Q&amp;A companion</title></head>
<body>

<h1>&lt;Source doc title&gt; — Q&amp;A companion</h1>
<p>Long-form answers to comments on
   <a href="https://docs.google.com/document/d/SOURCE_ID/edit">the source doc</a>.
   Each section records where the comment was left, what was asked, and the full response.</p>
<hr/>

<h2>Questions answered</h2>
<ol>
  <li><a href="#heading=h.xxxx">Q1 — short paraphrase of the question</a></li>
  <li><a href="#heading=h.yyyy">Q2 — ...</a></li>
</ol>
<hr/>

<h2>Q1 — short paraphrase of the question</h2>

<p><b>Where:</b> §4 "One step of the async RL trainer" &nbsp;|&nbsp;
   <b>Highlighted:</b> <i>"theta_old"</i> &nbsp;|&nbsp;
   <a href="https://docs.google.com/document/d/SOURCE_ID/edit?disco=COMMENT_ID">jump to the comment</a></p>

<p><b>Asked:</b> <i>"what is the point of restoring theta_t to apply optimizer step?"</i></p>

<h3>Answer</h3>
<p>...</p>

<p><i>Figure 01. What the diagram shows.</i></p>
<p>&nbsp;</p>

<hr/>
</body>
</html>
```

The index at the top is what makes the doc usable once it has more than about three sections.
Rebuild it whenever you append.

## Use `apply`, not `replace`

**Once the companion has a single comment on it, `replace` is the wrong command.** It overwrites the
whole body, which razes the text every comment is anchored to. The Docs API cannot re-anchor a
comment, so those threads survive as orphans: still open, attached to nothing, invisible in the
document. The CLI now refuses and offers to delete / resolve / orphan each one — all three are
wrong, because the human owns those threads.

Use `apply`, which computes the minimal edit from a base snapshot and leaves untouched paragraphs,
and their anchors, alone:

```bash
meta google.docs get --id="$COMPANION" > /tmp/comp.html   # base
# ... append the new section, update the index ...
meta google.docs apply --id="$COMPANION" --from=file:///tmp/comp.html --dry-run
meta google.docs apply --id="$COMPANION" --from=file:///tmp/comp.html --conflict-resolution=ours
```

Without a stored base snapshot `apply` self-fetches the live doc, which it will only do for a real
write if you pass `--conflict-resolution=ours` — that trades away offline conflict detection, which
is fine for a doc only this skill writes to. Then re-insert images for the new section only;
existing ones survive as `<img src="https://lh7-rt.googleusercontent.com/...">`.

This is a direct consequence of the companion being commentable. The moment you invite follow-ups
where the answer lives, whole-body overwrite stops being available — so reach for `apply` from the
first append, not after the first orphan warning.

Track the companion ID and pass it to the cron job as `--companion <id>` so repeat runs append
rather than creating a new doc each time.

Revising an existing section works the same way — get, edit that section in the exported ghtml,
replace. Two things to watch on a revision:

- **Leave the other sections byte-identical.** You are rewriting the whole body to change one
  paragraph; anything you reflow or "tidy" on the way past is an undiffed change to an answer the
  reader already accepted.
- **Comment anchors ride on text.** A comment attached to a phrase you rewrite goes orphaned, and
  the thread the reviewer is watching detaches from the paragraph it was about. If a follow-up asks
  you to change the exact text it is anchored to, add the correction adjacent rather than editing
  the anchor out from under it.

## The three required parts of a section

**Where they commented.** Section heading of the source doc, the highlighted text, and the
`?disco=` link from the comment's `url` field. Comments can be unanchored (`quoted_text: null`) —
say so and give the nearest heading, worked out from `ranges[0].start_index` relative to the
anchored comments around it. Do not invent a quote.

**What they asked.** Verbatim, in quotes. If the thread has follow-ups, include each one in order
with its own answer, so the section reads as the conversation it was.

**The full response.** Everything that did not fit in the margin.

## Figures

Reach for a figure when the answer has structure that prose has to serialize: a pipeline, a
before/after, a decision tree, two things being compared. Do not draw a figure for a fact.

Write one script that emits every figure for the run, using the bundled toolkit:

```python
import sys
sys.path.insert(0, "/home/<user>/.claude/skills/marginalia/scripts")
from figkit import *

fig, ax = canvas(14, 6.5)
headline(ax, "Where the gradient is measured", "Computed at one point, applied at another.")
box(ax, 6, 45, 38, 22, "theta_old", ["the policy that drew the samples"],
    fc=tint(BEFORE, .90), ec=BEFORE, tc=BEFORE, align="left")
box(ax, 56, 45, 38, 22, "theta_t", ["the live model, K steps later"],
    fc=tint(AFTER, .90), ec=AFTER, tc=AFTER, align="left")
arrow(ax, (45, 56), (55, 56), color=MUTED)
band(ax, 6, 20, 88, 14, AFTER, "gradient computed at theta_old, applied to theta_t")
save(fig, "01_where_measured")
```

Then run it and insert (see [gdoc-cli.md](gdoc-cli.md) for the upload/insert commands and the
landing-paragraph requirement).

Color discipline that keeps a multi-figure doc readable:

- One meaning per color for the whole doc. If orange is the ready-pool path in figure 1, it cannot
  be the error state in figure 4.
- Take categorical slots in the order `figkit` defines them. The order is what keeps adjacent pairs
  distinguishable under colorblindness; reordering silently breaks that.
- Status colors (`GOOD`, `WARN`, `CRIT`) are reserved. Never use one as "the third series".
- Every box carries a text label. Some palette slots sit under 3:1 contrast on the light surface, so
  color alone must never be the only thing carrying meaning.

## Equations

Google Docs has no math. Render each equation to a PNG with `figkit.equation()` and insert it like a
figure at 60-75% of text width, so it reads as display math rather than a diagram.

```python
equation(r"\nabla J(\theta) = \mathbb{E}_{a \sim \pi_\theta}\left[R(a)\, \nabla \log \pi_\theta(a)\right]",
         "eq_reinforce")
equation(r"r = \exp\left(\log \pi_\theta(a) - \log \pi_{\text{old}}(a)\right)", "eq_ratio")
equation(r"\mathcal{L} = -\min\left(r\hat{A},\ \mathrm{clip}(r, 1-\epsilon, 1+\epsilon)\,\hat{A}\right)",
         "eq_ppo_clip")
```

Give each an anchor caption so the insert can find it:

```html
<p><i>Equation 01.</i></p>
<p>&nbsp;</p>
```

**Size equations at native scale, not to the page.** A figure gets `--width 468` because it should
fill the column. Do that to an equation and every one lands at text width, so a two-symbol ratio
renders in 40pt type next to a full loss function in 11pt — the type size becomes noise that looks
like emphasis. Render at `dpi=220` and insert at the size the point-22 font actually implies:

```python
w, h = png_size(path)
width = min(round(w * 72 / 220), 468)      # 220 = the dpi equation() renders at
height = round(width * h / w)
```

Short equations then come out small, long ones come out wide, and the glyphs are the same size in
both — which is what display math looks like on a page.

Inline symbols in running prose stay as `<code>` — do not render a PNG for a lone `theta_t`. Images
break line flow and cannot be searched or copied.

Mathtext is a LaTeX subset. `\frac \sum \prod \int \sqrt`, greek, sub/superscripts, `\mathcal`
`\mathbb` `\mathrm` `\text`, and `\left(...\right)` all work. `\begin{align}` and `\begin{cases}` do
not — render one image per line and stack them, or use a monospace `<pre>` block, which is often
more honest for a derivation someone may want to copy.

## Writing the answer itself

- Lead with the finding. The reader clicked a link to get here; do not make them read setup first.
- Cite `file.py:line` for every code claim, and say plainly when something could not be verified.
- If this answer corrects something you said earlier, put the correction first and label it. A
  correction buried at the bottom is a correction nobody reads.
- Keep the register of working notes, not a report. No preamble, no "great question".

## ghtml notes

- Highlight a key result: `<span style="background-color: #B7E1CD"><b>...</b></span>`
  (green good / `#F4C7C3` bad / `#FCE8B2` caveat)
- Tables: `<table data-col-widths="200,150,150">`, header cells `<th style="background-color: #F0F0F0">`
- `<hr/>` between sections; numbered `<h2>` headings so the outline is navigable
- `<code>` for identifiers, `<pre>` for blocks
- Do NOT use `<img>` in the ghtml — it is ignored. Images go in via the insert command afterwards.
