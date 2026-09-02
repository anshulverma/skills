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

## Appending, not replacing

`meta google.docs replace` overwrites the whole body, so to add a section:

1. `meta google.docs get --id="$COMPANION"` — export current ghtml
2. Append the new section, update the index
3. `replace` with the merged file
4. Re-insert images for the new section only — existing ones survive the round trip as
   `<img src="https://lh7-rt.googleusercontent.com/...">` and are preserved

Track the companion ID and pass it to the cron job as `--companion <id>` so repeat runs append
rather than creating a new doc each time.

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
