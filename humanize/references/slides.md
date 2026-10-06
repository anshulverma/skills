# Slide decks

Read this when the doc is a slide deck. It replaces the target shape, the length rule and
read-back checks 4, 5, 7 and 8 in SKILL.md. The fact sheet, both fact checks, the transforms
and the link rules still apply, to the slides and to the speaker notes.

A deck has two layers. The slide is what the room reads in a few seconds while someone is
talking, so it carries the claim and its evidence. The speaker notes carry what the presenter
says: the qualifiers, reasons and caveats a slide has no room for. `fact_check.py` reads the
notes too, so a fact that moves off a slide into its notes still counts as kept.

## The target shape

- **A title slide that names the decision.** It holds the deck title (a plain claim of at
  most 8 words that names the system it is about), the presenter, the date, and one line
  saying what the room is asked to decide. It carries no TL;DR block.
- **Headline titles.** Each title states the slide's one point in 3 to 8 words, sentence
  case, with its number when it has one: "Three jobs sent 3.2M requests/min", not "Problem
  Statement". Reading the titles alone, in order, tells the whole story.
- **One point per slide.** A slide that needs two headlines becomes two slides.
- **At most about 30 words on a slide** below the title, table cells included: up to four
  bullets, each a fragment of at most 8 words that starts with its content, never a bold
  label. Full sentences and paragraphs go in the notes.
- **Numbers that stand on their own.** A number on a slide carries its unit, and when a
  decision rests on it, its reason in a few words ("9K rows/s cap: the RCA's coverage
  optimum"), because people read decks again later without the talk.
- **A visual on every content slide,** picked from the table in `visuals.md`: a card diagram
  of at most 5 boxes, a chart of real data, big-number cards, a table that compares values
  across its columns (at most 4 rows), or a timeline for phases. A list laid out as a table
  is still a list. The visual and the numbers behind it share one slide; a point is never
  split into a figure slide and a table slide. The title already says what the visual shows, so
  there is no "Figure N" caption and no "Figure 1 shows" sentence. A drawing of a rule rather
  than of data is marked "Illustration" on the slide and obeys the rule it draws.
- **Big-number cards:** the number, a label of 2 to 4 words, and a consequence tagline under
  it ("3.2M requests/min" / "on 10-01" / "tiers fall over at 2.0M").
- **Names the room can read.** Use plain names, or the term the audience already says out
  loud; other identifiers, and any term that needs defining, go in the notes. The exception
  is an identifier an ask or work item names: it stays on that slide, in backticks, because
  someone acts on it. There is no Nomenclature slide.
- **References as linked IDs.** A slide shows a diff, task or SEV as its bare ID, linked
  (S712241). Longer links go in the notes, or on one "Links" backup slide after the close.
- **Speaker notes of 2 to 6 sentences** per slide (about 40 to 120 words), written as the
  presenter would say them, carrying what the slide dropped. A note does not restate the
  slide. When the next slide needs a setup, the note ends with a handoff phrased for that
  slide ("So has anyone typed that number?"), not a stock "Next:" line on every note.
- **An ending that concludes and asks.** The last slide states the conclusion in one line,
  in words that add to the title slide rather than repeat it, then the asks (what, from
  whom, and by when if the source gives a date). Open questions the room must discuss get
  their own slide before it, written out in full. This replaces "Key takeaways",
  "Questions?" and "Thank you" slides.
- **An agenda or section dividers only in a deck of more than about 15 slides.**

Slide count follows the points and usually stays within about a third of the draft's: a
10-slide draft comes back as 8 to 13. On-slide words
usually fall by half or more while the notes grow, so the 5 percent length rule does not
apply. Never drop a fact to fit a slide: move it to the notes.

## The working format

Write every version as markdown, one slide per block, with a line holding only `---`
between slides:

```
# Three jobs sent 3.2M requests/min

![Load against tier capacity](figure-1.png)

Notes: On 10-01 three jobs ran at 20K, 20K and 14K rows per second. The shadow tiers
collapse between 2.0 and 2.3M AdFinder requests a minute, so they crash-looped.
```

Keep the notes marker the source uses (`Notes:` or `>`) so the deck round-trips. For a
Google Slides deck, `v0.md` is `meta google.slides get --id=<id> --output=markdown`,
which marks speaker notes as `>` lines and has no separators. Insert a `---` line before
each slide's title, checking the count against the slide summary from
`meta google.slides get --id=<id>`.

## Score

Score decks with `slop_score.py --type slides`. It weighs AI tells and bold across slides
and notes, words on each slide over 30, notes over 150 words, titles over 8 words,
topic-label titles ("Agenda", "Background", "Key Takeaways"), content slides with no
visual, and unlinked references. `--detail` lists every slide that breaks a limit. Its word
count is on-slide words only.

| Score | Seen in testing |
|---|---|
| 84 | An agent-drafted bullet deck, topic titles, no visuals |
| 35 | An agent-drafted deck with headline titles and images, 10-15 word titles, notes of about 200 words |
| 31 | The bullet deck after the prose-only version of this skill: paragraphs on slides |
| 0-1 | Both decks after this reference |

The target is 15 or below.

## Deliver to Google Slides

Work in a copy so the original survives (`meta google.slides copy`), and tell the user which
deck is which. `meta google.slides export --id=<id> --dest=file:///tmp/humanize/<doc>/deck.html`
gives ghtml; carry each slide's text into its elements and apply it. `apply` cannot move or
resize elements or add slides, so use `meta google.slides.slide` to add, delete or move
slides and set their notes, and `meta google.slides.content` to add images and shapes (see
`meta google.slides --help`). Then run `meta google.slides lint --id=<id>`, look at each
slide's `meta google.slides.slide thumbnail`, and fix any overflowing text box.

## Read-back checks for a deck

1. The titles read alone, in order, tell the story; none is a topic label and none is over
   8 words. The title slide names the system and the decision.
2. No slide carries more than about 30 words, four bullets or a full paragraph below its
   title.
3. Every content slide has a visual, each rendered and looked at, with no figure captions,
   and no table that is a list in disguise. The slide count is within about a third of the
   draft's.
4. Every fact that left a slide is in that slide's notes, and no note is a wall.
5. The last slide gives the conclusion and the asks with their owners, and the open
   questions are written out on a slide of their own.
6. The only identifiers on slides are ones an ask or work item names, and every number on
   a slide has its unit.
