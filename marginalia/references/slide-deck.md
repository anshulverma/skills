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
6. **Lint.** `meta google.slides lint --id="$DECK"`. Fix the errors; read the warnings.
7. **Goal.** Read the goal, then the last slide. Did you get there?
