# Building the synthesis doc

The source doc is what someone wrote. The companion is what you asked about it. The synthesis is
**what the two of them add up to, written for someone who asks nothing.**

That last clause is the whole design. A reader of the companion is following your questions. A
reader of the synthesis has no questions yet, because they do not know enough to have any. They get
one shot at the material in one order, and the order is your job.

## It is not a merge

The tempting failure is to concatenate: source doc sections, then companion answers appended where
they are relevant. That produces a longer document, not a clearer one, and it is obvious from the
outside because the seams show:

| Seam | What it looks like | What it means |
|---|---|---|
| Question-shaped headings | "Why does the scorer run single-threaded?" | You kept the companion's spine |
| "As discussed above in §4" | Cross-references doing the work of structure | The order is wrong |
| A section that opens with a caveat | "Note that unlike the earlier claim..." | A correction never got absorbed |
| Two sections explaining the same mechanism | Once from the source, once from an answer | You appended instead of folded |

**If a section still reads like an answer to a question, it has not been synthesized.** The question
should have disappeared into the structure: the thing you had to ask about is the thing the reader
needs explained early, which means it earned a section, not a Q&A entry.

## The outline is the product

Write the outline before any prose, and treat it as the artifact under review. A wrong sentence
costs a sentence; a wrong outline costs the document.

Build it by asking, in order:

1. **What does the reader need to be able to do at the end?** One sentence. Write it down — it goes
   at the top of the doc and it is what every later cut is measured against.
2. **What is the smallest set of ideas that gets them there?** Not everything you learned. The
   companion holds everything you learned; this holds what is load-bearing.
3. **What depends on what?** Sort by dependency, not by importance and not by the source doc's
   order. The source doc was written by someone who already understood it, so its order is almost
   never the teaching order.
4. **Where does each one land — body or appendix?** Body if the spine breaks without it. Appendix
   if it is true, interesting, and skippable.

Keep the outline in the doc as a short "What this covers" list under the goal. It is the index and
it is also the promise.

## Two update modes, and picking wrong is what rots the doc

The synthesis is rewritten, not appended to. But rewriting the whole thing on every new answer
churns text the reader already accepted and burns a rebuild for a one-paragraph change. Two modes:

**Fold in** — the default, whenever the companion gained or changed an answer. Find the section that
already owns that idea and extend it: sharpen the explanation, add the caveat, correct the claim,
add a figure. If the material genuinely has no home, add one section in the right dependency
position — not at the end because that is where the cursor was.

**Reorganize** — rarer, and triggered rather than scheduled. Re-plan the outline and rewrite when:

- You folded something in at the end because nothing fit. Once is an accident; twice means the
  outline no longer describes the material.
- The build-up order broke — something is now explained using a term introduced below it.
- An answer changed what the document is fundamentally about, not just what it says.
- A comment on the synthesis says the reader got lost. That is the outline failing, and patching the
  paragraph they got lost in will not fix it.

Say which mode you used in the report line. "Folded Q12 into §3" and "reorganized, §3 and §4 swapped
because the staleness window is needed before the queue math" are different events and the reader
should be able to tell them apart.

## The four rules, as checks you can actually run

Rules that cannot be checked are wishes. Each of these has a pass.

### 1. No walls of text

One idea per paragraph. If a paragraph needs "and also", a semicolon, or a second "because" to hold
together, it was two paragraphs, a list, or a table.

- Hard cap: **no paragraph over four lines.** Not a style preference — a five-line paragraph on a
  screen is a block the eye slides off, and the reader stops reading before they decide to.
- Lead every section with its conclusion. The reader should be able to read only the first sentence
  of each section and come away with the correct summary.
- Cut every sentence that describes the document instead of the subject. "In this section we will
  examine..." is a line the reader pays for and learns nothing from.

**The pass:** read only the first sentence of every paragraph, top to bottom. If that reads as a
coherent summary, the structure is right. If it reads as fragments, the paragraphs are carrying
ideas their opening sentences do not name.

### 2. A visual wherever there is structure

In the companion, a figure supports the prose. **Here it is inverted: the figure is the explanation
and the prose annotates it.**

Any section describing a process, a comparison, a hierarchy, a flow, a state machine, or a
before/after opens with the figure. Prose that serializes something inherently two-dimensional is
prose the reader has to re-assemble in their head, and they will do it wrong.

The tell: you wrote three paragraphs and then thought "a diagram would help here." It would, and it
replaces two of them. Draw it, then delete what it made redundant — the common half-measure is
adding the figure and keeping all the prose, which leaves the reader reading the same thing twice
and trusting neither.

Do not draw a figure for a fact. A number, a name, a single cause-and-effect: those are sentences.
Figures are for relationships.

Figure mechanics, palette discipline, and the one-script-per-run rule are in
[companion-doc.md](companion-doc.md) — same toolkit, same colour-means-one-thing rule, and the
meanings must agree across the companion and the synthesis so a reader moving between them is not
relearning the legend.

### 3. Build up — nothing is used before it is earned

**Every term is introduced in the body at the point it is first needed.** The appendix glossary is
the backstop for a reader who skipped around, not the mechanism. A reader going top to bottom should
never have to jump.

This is stronger than it sounds, because it constrains order, not just vocabulary: each section must
be readable by someone who has read only the sections above it.

**The pass — run it on every rebuild, it is cheap and it catches real bugs:**

- Walk the doc top to bottom keeping a set of terms already introduced. Every technical term, config
  name, component, and acronym on first use must be either defined in that sentence or already in
  the set. A hit is a real defect, not a nitpick.
- Then cover everything below section N and ask whether §N still makes sense. If it needs something
  from below, either move it up or you have the dependency backwards.

When the source doc's own order violates this — and it usually does, because it was written by
someone who already knew the material — **follow the dependency order, not the source.** Note the
remapping once near the top so a reader holding both documents is not confused about why §3 here is
§7 there.

### 4. Every equation is explained

Math earns its place by being more precise than the sentence, not by being present. If a sentence
says it, write the sentence.

When an equation does earn its place, it carries three things and never fewer:

1. **What each symbol is** — a short table or a line per symbol, in the order they appear. No
   symbol arrives unnamed.
2. **What the equation says, in words.** One sentence, no symbols in it. If you cannot write that
   sentence, you do not yet understand the equation well enough to publish it.
3. **Why it matters here** — what it lets the reader conclude, or what changes if a term moves.

Never an equation followed immediately by the next heading. That is a formula the reader scrolls
past, and it makes the document look rigorous to someone who is not reading it, which is the only
audience it serves.

Rendering (mathtext, sizing at native scale, the `dpi=220` convention) is in
[companion-doc.md](companion-doc.md). The obligation above is on top of it.

## Structure

```html
<html>
<head><title>&lt;Source doc title&gt; — explained</title></head>
<body>

<h1>&lt;Source doc title&gt; — explained</h1>

<p><b>What you will be able to do after reading this:</b> &lt;one sentence&gt;</p>
<p>A reorganized, plain-language walkthrough of
   <a href="https://docs.google.com/document/d/SOURCE_ID/edit">the source doc</a>, incorporating the
   answers worked out in
   <a href="https://docs.google.com/document/d/COMPANION_ID/edit">the Q&amp;A companion</a>.
   Sections are ordered so each one only needs the ones above it.</p>

<h2>What this covers</h2>
<ol>
  <li><a href="#heading=h.xxxx">1. The problem this system solves</a></li>
  <li><a href="#heading=h.yyyy">2. ...</a></li>
</ol>
<hr/>

<h2 data-heading-id="h.xxxx">1. The problem this system solves</h2>
<p>&lt;conclusion first, four lines maximum&gt;</p>
<p><i>Figure 01. What the diagram shows.</i></p>
<p>&nbsp;</p>
<hr/>

<h2>Appendix A — Glossary</h2>
<p>Ordered so no definition leans on a term defined below it. Comment on any term that is still
   unclear and it gets added.</p>
<table data-col-widths="180,420">
<tr style="background-color: #F0F0F0"><th>Term</th><th>What it means here</th></tr>
<tr><td><code>staleness window</code></td><td>...</td></tr>
</table>

<h2>Appendix B — Details that did not fit the spine</h2>

<h2>Appendix C — Where this came from</h2>
<p>Which source-doc section and which companion answer each section draws on, so a reader can go
   back to the long form.</p>
</body>
</html>
```

Appendix C is cheap to maintain and it is what stops the synthesis from becoming a third
un-auditable account of the system. Every claim in the body should be traceable to the source doc,
a companion answer, or a pinned code citation.

## Writing and updating it

Everything in [companion-doc.md](companion-doc.md) about **`apply`, not `replace`** applies here
verbatim, and harder: the synthesis is rewritten far more often than the companion is appended to,
so it accumulates comment anchors and then walks over them.

- `get` to a base snapshot, edit, `apply --dry-run`, then `apply --conflict-resolution=ours`.
- Watch the `Comments: ... N reopened` line. Non-zero means you moved thread state that belongs to
  the reader.
- A reorganize *will* orphan comments — that is what moving text does. Before a reorganize, read the
  open threads on the synthesis, make sure each one's substance is absorbed into the new text, and
  say in the report which threads were anchored to text that moved.

Cite code the same way, with the same pinned commit, using the link form in
[companion-doc.md](companion-doc.md). A synthesis with unlinked `file.py:88` pointers is a document
the reader has to take on faith, and the reader of the synthesis is precisely the one with no
standing to check.
