# Building the deck

The deck is the synthesis doc with the reading removed. Same material, same order, but a document is
read by one person at their own pace and a deck is talked through to a room at yours — so the deck
carries less and the person presenting carries the rest.

It derives from the synthesis, never from the source doc or the companion directly. If something
belongs on a slide it belongs in the synthesis first, where it can be checked; a claim that exists
only in the deck is a claim nobody reviewed.

## Start from the goal, and write it down

One sentence: **"after this, the audience can ___."** Put it in the speaker notes of slide 1 and keep
it there. It is not a slide — nobody wants to watch you read your own objective — but every later
question resolves against it:

- Does this slide move the audience toward it? Keep it.
- Is it true, interesting, and not on the path? Appendix.
- Neither? Cut.

Without a written goal, "is this slide worth a minute" has no answer, and the deck grows until it
hits the time limit instead of until it is done.

If the goal is not obvious from the material, ask in a comment on the synthesis rather than guessing.
Two plausible goals — "convince the team to adopt this" and "teach a new hire how it works" — produce
different decks from the same doc, and building the wrong one is a whole rebuild.

## The spine: write the titles first

**Every slide title is a full-sentence claim, not a topic label.** "Scoring architecture" makes the
room listen to find out what about it. "One scoring batch is in flight at a time" tells them in two
seconds, and then the picture underneath is evidence they can inspect while you talk.

So write the deck as a list of sentences before you make a single slide. That list *is* the talk.
Read it top to bottom:

- Does it tell the story on its own? If the titles alone are a coherent argument, the deck will be.
- Does each one answer a question the previous one raised? That is what "a journey" means
  operationally — not a narrative flourish, a dependency chain. Slide N+1 exists because slide N
  made the audience wonder something.
- Does the last one state the goal as achieved? If not, either the spine stops short or the goal
  was wrong.

Fix the spine at the sentence-list stage. A wrong spine discovered at slide 20 costs twenty slides.

## Rules on a single slide

**Fewer words, more picture — and the words go somewhere, not away.**

- Title: one claim, ideally under 12 words.
- Body: **25 words maximum**, and that is a ceiling, not a target. Most slides should be a figure
  and a label.
- Never a paragraph. Never a bullet that wraps to a third line. If a bullet needs a sub-bullet, the
  slide is two slides.
- One idea per slide. Two claims on a slide means the audience picks one and you do not get to
  choose which.

Everything you removed goes into the **speaker notes**, in full sentences. This is the mechanic that
makes the rule survivable: the deck stays readable for whoever opens it six months later without
you, and the slide stays clean for the room. Notes are not optional — a slide with a bare figure and
no notes is a slide only you can present.

Figures come from the synthesis. Reuse them rather than redrawing: the audience that read the doc
recognises them, and the colour-means-one-thing discipline already holds across both. A synthesis
figure is usually too dense for a slide, though — the honest move is to split it into the two or
three progressive versions you would have drawn on a whiteboard, one per slide, each adding a layer.
That progressive build *is* the complexity ramp, and it costs nothing but slides, which are cheap
inside the budget.

## The grid, and why a figure slide breaks without one

**Put every element on a stated grid, and re-place the text every time you add a figure.**

The failure this prevents is specific and it is silent. `content add-image` / `insert-image` drops
the picture at a default position — in one real build, every single figure landed at the same
`y=430 h=330` — and it does **not** move the body text out of the way. The body keeps the position
the layout gave it, the figure covers it, and the slide looks fine in the thumbnail strip because
the title is still legible. Twelve figure slides had their body text 70–80% underneath the picture
before anyone opened one full-screen.

Nothing catches this for you. `google.slides lint` checks palette and writing style, not geometry.

So fix the regions once and drive every slide to them. Normalised to a 1440 × 810 pt canvas (the
common Meta template; scale proportionally if `pageSize` differs — Google's plain 16:9 default is
720 × 405):

| Archetype | Title | Body | Figure |
|---|---|---|---|
| **Text** (title + prose) | 120, 180, 1200 × 80 | 120, 290, 1200 × 440 | — |
| **Figure** (title + legend + picture) | 120, 150, 1200 × 76 | 120, 238, 1200 × 70 | fit inside 120, 326, 1200 × 424 |
| **Divider** (centred claim) | 120, 330, 1200 × 150 | — | — |
| **Section** (eyebrow + big title) | 120, 280, 1200 × 180 | eyebrow stays at 34, 34 | — |

Read as `x, y, w × h` in points. Side margin 120, nothing below y=750.

Three things that make the grid hold rather than drift:

- **The figure is fitted, not placed.** Scale by `min(box_w/img_w, box_h/img_h)` and centre it in the
  box. Never set width and height independently on an image — it silently stretches the figure, and
  a stretched axis label is the kind of thing nobody reports and everybody notices.
- **The body on a figure slide is a legend, not prose.** 70 pt of height is one or two lines on
  purpose. If the text does not fit, the sentence belongs in the notes, not in a taller box.
- **Delete duplicate placeholders, keep empty theme slots.** A multi-column layout used for a single
  point leaves unfilled TITLE/BODY columns behind, and those are what the figure gets laid over —
  delete them. But the empty eyebrow/footer/presenter slots the template puts on every slide render
  as nothing and every other slide has them; removing those makes the deck less consistent, not more.

Adopt the template's own layouts rather than inventing a look — `google.slides.layout list` shows
what the master already has (a corporate template typically ships 20+: title, section, text, two-
and three-column, big-stat). The grid above is where content goes *within* whichever layout you
picked; it is not a replacement for the theme.

## The budget, and what to do when you blow it

Thirty minutes presented. The arithmetic that actually holds:

| | |
|---|---|
| Opening — title, why you are here, where this is going | 2 min |
| A content slide with a figure, talked through | 60–90 s |
| Interruptions and questions during the body | ~20% overhead |
| Closing — what to take away, what to do next | 2 min |

That lands at **18–22 content slides. Treat 25 as the hard cap**, plus a title and a closing.

When you are over: **move down, do not compress.** Cutting a slide's words to fit one more slide in
produces two bad slides instead of one good one. The appendix has no budget — that is what it is
for. Deciding what moves is the same question as before: does the spine break without it?

A deck that runs long is not a deck that needs faster talking. It is a deck whose goal was too broad,
and the fix is upstream.

## The appendix

Relevant but not required. The test is concrete: **an appendix slide is one you would actually flip
to when someone asks a question.** So title it with the question it answers — "How does the staleness
window interact with the queue depth?" — because the only way you will find it live is by reading
the titles while a room watches.

Good appendix material, roughly in order of how often it gets used:

- The derivation, the full table, or the raw numbers behind a body slide that shows only the
  conclusion.
- The alternative that was considered and rejected, with why.
- The mechanism one layer below what the body needed — the thing the one person in the room who
  already knows this will ask about.
- Definitions, for a mixed-seniority audience.
- Where to go next: the synthesis doc, the companion, the source doc, key code pointers.

Keep an appendix index slide if there are more than about six, for the same reason the docs have
one.

## Keeping it in sync with the synthesis

Maintain a mapping — synthesis section to slide numbers — in the speaker notes of the title slide.
It is three lines and it is what makes an update a targeted edit instead of a re-read.

| What changed in the synthesis | What happens to the deck |
|---|---|
| A section was folded into, wording only | Usually nothing. Update only if a slide quotes the changed claim |
| A section gained a figure or a correction | Update the slides that section maps to |
| A new section was added | Decide body or appendix by the spine test, then insert in dependency order |
| The synthesis reorganized | Re-derive the spine from the new outline, then rebuild. Do not reorder slides in place — the spine is the thing that changed |
| The goal changed | Full rebuild. Everything downstream of the goal is now unverified |

Do not rebuild the deck on every sweep. Rebuild it when the synthesis changed in a way the table
above says it should — and say which rows fired, in one line.

## Mechanics

Commands, flags, and the traps are in [slide-deck-cli.md](slide-deck-cli.md). Four things there
change how you *write* a slide, so they belong here too:

- **Slides ghtml is not Docs ghtml.** No `<h1>`–`<h6>`, no `<pre>`, no `<code>`, no `<th>`. A title
  is a `<p>` in the title box. An identifier survives as plain text — which is usually right on a
  slide anyway, but it means the `<code>`-everything habit from the companion doc produces nothing.
- **Layout is fixed when the slide is created.** There is no retrofitting `TITLE_AND_BODY` onto a
  slide that started `BLANK`; you rebuild it. So decide the layout when you decide the slide, not
  after you see how much text there is.
- **Images go straight into the ghtml** with `width`/`height` on the tag — none of the Docs
  upload-then-insert-then-anchor sequence. A 16:9 slide is 720 × 405 pt; a figure under a title row
  gets about 720 × 300. Render at that aspect ratio rather than squeezing a 14×6.5 doc figure in.
- **60 writes per minute.** A deck built one `insert-text` at a time earns 429s. Batch it.

And `meta google.slides lint --id="$DECK"` is free — it catches small fonts, off-palette colours,
and em-dash overuse. Run it; it is a second opinion that costs one command.

## Review every slide, by looking at it

**A slide is not finished when the text is written. It is finished when someone has looked at the
rendered picture of it and not found anything wrong.**

Everything in this file up to here can be satisfied by a slide that is unreadable in a room. The
checklist below catches wording. It does not catch a legend at 8pt, a badge sitting on top of the
word it labels, or a figure whose own heading contradicts the title above it — and in one real deck
all three were present on slides that passed every text-level check and a clean geometry audit. They
were found the first time anybody rendered a PNG and looked.

So: **render the slide, then review the render.** Not the ghtml, not the plan — the image.

```bash
meta google.slides.slide thumbnail --id="$DECK" --page-id="$PAGE" --save-to=/tmp/shots/slide-07.png
```

### Dispatch several reviewers per slide, each with the screenshot

One reviewer with a long checklist does all of it badly — it satisfices, finds two things, and
stops. Separate readers, each with one question and no knowledge of the others' findings, disagree
productively. **Every reviewer gets the PNG path and is told to actually open it**, because an agent
handed an image and a text description will quietly review the description.

Run them in parallel, one batch per slide (or per small group of slides), with these angles:

| Angle | The one question it answers |
|---|---|
| **Look** | Is anything overlapping, clipped, off-canvas, misaligned, or too small to read from the back of a room? |
| **Feel** | Does it look like it belongs to the same deck as its neighbours — same margins, same type scale, same density? |
| **Understandability** | A reader who has not read the doc: what do they take away in eight seconds, and is that the claim the title makes? |
| **Adversarial** | Attack it. What is the most embarrassing question from the room, what does the slide overclaim, what does the figure quietly assume? |
| **Truth-vs-source** | Does every number and claim on the slide, *including inside the figure*, match the synthesis section it came from? |

Give each one the image, the slide's title and body text, its speaker notes, and — for the last two
— the synthesis section behind it. Ask for a short list of concrete defects and nothing else; a
reviewer that returns prose returns opinions.

Three rules that decide whether this is worth running at all:

- **The figure is part of the slide.** Most defects in practice are *inside* the picture: type that
  was legible in a doc and is not on a projector, annotation labels that collide once the figure is
  scaled, and captions that still assert what the slide title was corrected away from. A reviewer
  told to check "the slide" will check the text; say *including the figure* or it will not look.
- **A contradiction between the figure and the title is a content bug, not a layout bug.** It means
  the title was fixed and the figure was not, so the synthesis behind it is probably also stale.
  Chase it upstream rather than editing the caption.
- **Do not act on style opinions.** Tell reviewers to report only what they can see, and to leave
  wording, colour taste, and "could be punchier" alone — otherwise the pass becomes a rewrite and
  you lose the slide you already agreed on.

Fix, re-render, and re-review the slides you changed. A defect list you did not re-check is a
defect list.

## Checks before you call it done

Run these in order; each one is cheap and catches a different failure.

1. **Titles only.** Read the title of every body slide in order, nothing else. Coherent argument, or
   a list of topics?
2. **Word count.** Any body over 25 words, any wrapped bullet, any paragraph — fix before anything
   else.
3. **Notes present.** Every slide. A slide you cannot hand to someone else is half a slide.
4. **The ramp.** Cover every slide after slide N — does slide N still make sense? Same invariant as
   the synthesis: nothing used before it is earned. A term that first appears on slide 14 with no
   slide having introduced it is the most common way a deck loses the room, and it is silent —
   nobody puts their hand up to say they stopped following four slides ago.
5. **Count and time.** Under the cap, or the overflow is in the appendix.
6. **Lint.** `meta google.slides lint --id="$DECK"`. Fix the errors; read the warnings. It checks
   palette and writing style only — **not geometry, not legibility**, so it passing means nothing
   about whether the deck can be read.
7. **Geometry.** Compute every element's rectangle from `--output=raw-json` and assert no text box
   intersects an image. See the grid section; this is the check that would have caught twelve
   figure-over-body slides in one pass.
8. **Render and review.** Screenshot every slide and run the reviewer angles above. Nothing else in
   this list looks at the actual pixels, and that is where the defects were.
9. **Goal.** Read the goal, then the last slide. Did you get there?
