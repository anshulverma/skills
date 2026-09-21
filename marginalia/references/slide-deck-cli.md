# Google Slides CLI cookbook

Everything here was learned by hitting the failure first. Each gotcha below cost a round trip;
reading this costs you nothing.

Slides has the same **create → apply** pair `google.docs` has, and almost none of the same flags.
Copying a docs invocation across is the single most reliable way to waste a turn.

## Create the deck

```bash
# ghtml source: slides delimited by <hr>
meta google.slides create --from-html=file:///tmp/deck.html --template=meta

# markdown source: --- delimits slides, "# heading" becomes the title placeholder
meta google.slides create --from-markdown=file:///tmp/deck.md --template=meta --title="Q4 Review"

meta google.slides create --title="Kickoff" --template=meta            # empty themed canvas
meta google.slides create --title="X" --dss-level=DSS-4 --dry-run
```

`--file` and `--from` do **not** exist on `create`. It is `--from-html` / `--from-markdown`. There
is no `<title>` inference as in docs — the title comes from the first heading, else `--title`.

**`--from-html` will not build you a real deck.** Verified against a live deck: every `<p>` in a slide
block is concatenated into ONE text box joined by `<br/>`, so there is no title/body split; `<img>`
is silently dropped; and `<aside class="speaker-notes">` lands in the body as visible text rather
than as notes. You get the right number of themed slides and nothing else. Build slides with
`slide add` instead, and set notes and images per slide — see below.

**`--template=<name>` ships the template's whole sample gallery.** `--template=meta` created a deck
with **29 boilerplate slides** before any content of mine. `--from-html` with the same template
creates only your slides — that is the one thing the ghtml path is good for. If you build with
`slide add` on a templated deck, your slides land *after* the boilerplate; `slide delete` is
HUMAN_MUST_CONFIRM, so the no-confirmation move is `slide move` to push the boilerplate past your
content and ask the user to delete it.

**Pick the theme now or never.** The Slides API cannot theme an existing deck, so `--template` at
create time is the only way to get one. It takes a registry name, a presentation ID/URL, or `none`.
`meta google.slides.template list` returns 22: `meta, indigo, teal, green, orange, red, purple,
general-starter, eng-starter, reality-labs, infra, simple-dark, material, streamline, slate,
spearmint, focus, momentum, coral, paradigm, modern-writer, geometric`.

`meta google.slides lint --id="$DECK"` exits non-zero on an error-severity finding (small fonts,
off-palette colors, em-dash over-use). `create`/`apply` take `--lint-ignore=<rule>`, which requires
`--lint-ignore-reason`.

## Update it without destroying it

```bash
meta google.slides export --id="$DECK" --dest=/tmp/deck.html   # also writes /tmp/deck.html.base
# edit /tmp/deck.html
meta google.slides diff  --id="$DECK" --from=file:///tmp/deck.html
meta google.slides apply --id="$DECK" --from=file:///tmp/deck.html --dry-run --strictness=warn
meta google.slides apply --id="$DECK" --from=file:///tmp/deck.html
```

Three-way merge against `--base` (defaults to `<from>.base`). With `--from` omitted, `apply` reads
`/tmp/meta-ghtml-{PRESENTATION_ID}.html`.

**`apply` is not a whole-deck rewrite.** It updates text in place per `data-object-id`, creates
elements whose `data-object-id` is new, and leaves elements you did not export alone. It **cannot
move, resize, or change backgrounds** — that is `meta google.slides.content batch`. Keep the
`<meta name="revision-id" ... data-readonly>` line; apply checks against it.

`--strictness=off|warn|error` (round-trip verification) defaults to **off**, so an edit that does
not round-trip lands silently. Pass `--strictness=warn` while iterating.

Do not reach for the docs flags: slides `apply` has no `--conflict-resolution`, no
`--allow-comment-deletion`, no `--watch`. There is no `meta google.slides replace` at all —
attempting it errors with "not a valid action".

Comments survive an apply because they are not in the ghtml. The only `<aside>` in the dialect is
`class="speaker-notes"`; comments live in a separate namespace, so apply has no mechanism to touch
them. This is a real difference from Docs, where the export carries comment *status* and a stale
base can un-resolve a thread.

## The two ghtml dialects

`meta google.slides ghtml` (no `--id`) prints the format reference. Slides ghtml is a **different
dialect from Docs ghtml** and reuses two Docs tags for other meanings.

- **Creation** (`create --from-html`): slides are delimited by `<hr>`.
- **Round-trip** (`export` / `apply`): slides are comments.
  ```html
  <!-- gslides:slide:0 "p" -->
  <!-- gslides:bg:#F7F7F7 -->
  ```

Carrying `<hr>` into an apply file, or slide comments into a create file, is the first trap. In
Docs ghtml `<hr>` is a horizontal rule / page break.

Vocabulary: text boxes are `<p>` (one per paragraph, `<ul>`/`<ol>` for bullets), `<table>`, `<img>`,
`<aside class="speaker-notes">`. Inline: `<b> <i> <u> <s>`, `<a href>`,
`<span style="font-size: 24pt; font-family: Arial; color: #ff0000; background-color: #ffff00">`,
`<p style="text-align: center">`.

Absent from the reference, so assume dropped or unstyled (INFERRED — the reference simply does not
list them): `<h1>`–`<h6>`, `<pre>`, `<code>`, `<thead>`/`<th>`, `data-col-widths`, `<embed>` (no
mermaid / Daiquery / CodeHub embeds), smart chips. `lint --category=writing_style` flags "excessive
inline code".

Two of those bite a skill coming from the docs side. **There are no headings** — a slide title is a
`<p>` in the title box, so the `<h2>`-per-section habit produces unstyled body text. And **there is
no `<code>`**, so an identifier has to survive as plain text; on a slide that is usually right
anyway, but it means a code pointer cannot be styled, only linked.

**`<aside>` is repurposed.** In Docs it is a colored callout; here it is speaker notes. A Docs-style
`<aside style="background-color:#E8F0FE">` will not render as a box.

**Title/body/columns are not expressible in ghtml.** Export gives
`<p data-object-id="title_box" data-x="508000" data-y="508000" …>` — the ID is a name, not a
placeholder role, and there is no layout attribute. Layout is fixed at slide-creation time, and
`slide set-layout` exists only to tell you Google cannot change it — rebuild the slide instead.
Two columns = two `<p>` boxes with different `data-x` (EMU, 12700 per pt). There is no two-column
predefined layout.

## Add, reorder, and delete slides

```bash
meta google.slides.slide list --id="$DECK" --output=json     # index, page_id, layout, element_count
meta google.slides.slide add --id="$DECK" --layout=TITLE_AND_BODY --title="T" --body="B" --index=2
meta google.slides.layout list --id="$DECK" --output=json    # -> layout_id for a custom theme layout
meta google.slides.slide add --id="$DECK" --layout-id="$LID" --title="T"
meta google.slides.slide duplicate --id="$DECK" --page-id="$PAGE" --index=0
meta google.slides.slide move --id="$DECK" --page-ids="$P1,$P2" --index=3 --dry-run
meta google.slides.slide delete --id="$DECK" --page-id="$PAGE" --yes-i-am-sure
meta google.slides.slide thumbnail --id="$DECK" --page-id="$PAGE" --save-to=/tmp/s.png
```

There is no `slide create`; it is `add`, and `add` returns the new page id — grab it from the output,
you need it for notes and images. `move` takes plural `--page-ids` (comma-separated) and a 0-based
`--index`, both required.

**`--index` on `move` means "insert before the slide currently at index N", counted in the
pre-move arrangement.** It is not the final position. Moving 29 slides to `--index=35` on a 64-slide
deck put them at position 6, not 35, because index 35 *was* the 6th of my slides. To move a block to
the very end, pass the total slide count.

Built-in layouts: `BLANK, TITLE, TITLE_AND_BODY, TITLE_ONLY, SECTION_HEADER,
SECTION_TITLE_AND_DESCRIPTION, ONE_COLUMN_TEXT, MAIN_POINT, BIG_NUMBER` — **but a themed deck
usually has none of them.** `--layout=TITLE_AND_BODY` on a `--template=meta` deck errors with "not
present in the current master". Resolve a real id first:

```bash
meta google.slides.layout list --id="$DECK" --output=json   # layout_id + display_name
meta google.slides.slide add --id="$DECK" --layout-id="$LID" --title="T" --body=$'line one\nline two'
```

The `meta` template's useful ones, by display name: `01_Title`, `22_Section`, `28_Text`
(the workhorse), `49_Points (Two)`, `52_Points (Three)`, `40_Columns (Two)`, `58_Big Stat`,
`79_End Card_White`. `--body` takes embedded newlines and renders them as separate bullets.

**Adding a slide is `slide add`, not `apply`.** The apply reference documents creating *elements*
with new IDs and says nothing about creating slides (INFERRED — see "Not verified").

## Put an image on a slide

```bash
meta google.slides.content add-image --id="$DECK" --page-id="$PAGE" \
  --file=file:///tmp/fig.png --x=40 --y=90 --width=4in --height=2.35in

meta google.slides.content add-image --id="$DECK" --page-id="$PAGE" \
  --image-url="$URL" --x=40 --y=90 --width=468 --height=274
```

`--x/--y/--width/--height` are points when bare, or take an `in`/`pt` suffix. Default placement is
(100,100) at 300x300pt. `--file` and `--image-url` are mutually exclusive.

**The older top-level `meta google.slides insert-image` takes inches for the identically named
flags.** `--width=468` there is a 468-inch image; `--width=4` on `content add-image` is a 4-point
one. Prefer `content add-image` and never mix the two in one script.

Inside ghtml, size goes on the tag — no separate insert command, unlike the Docs workflow:
`<img src="https://…/chart.png" width="400" height="300" />`. `apply` uploads `file://` `<img src>`
for you when reading from a file; for a URL you need inline, run
`meta google.slides upload-image --file=file:///tmp/fig.png` first.

`content add-image --file=file://...` uploads and places in one call — no `google-mux` detour, no
`--after-text` landing-paragraph dance. That part is genuinely easier than Docs.

**Measure the slide before you place anything; do not assume 720 × 405.** A default Google 16:9
slide is 720 × 405 pt, but a branded template need not be, and the `meta` template is
**1440 × 810 pt**. Placing against the wrong assumption is silent: the coordinates are accepted, the
API reports success, and every figure lands at half scale on top of the title. Two passes were
wasted on this before a thumbnail showed it.

**An earlier version of this file said the clear band on layout `28_Text` was "y 430 to 760" and
gave `--y 430 --height 330` as the recipe. That was wrong and it shipped.** The body placeholder on
that layout runs to **y 680**, not 380, so every figure placed by that recipe landed on top of the
body text. It reached twelve slides in one deck before anyone opened one full-screen — the title is
still legible in the thumbnail strip, so nothing looks wrong until you present it.

Do not place a figure against a remembered band. Read where the body actually ends, put the figure
below it, and check afterwards. The layout numbers vary per layout, and a deck usually mixes
several.

**Read geometry from `--output=raw-json`, never from the ghtml.** The ghtml carries `data-width` /
`data-height` straight off the element's `size` field and drops the transform, so a title reported
as `3000000 × 3000000` is really `size × scaleX` — on one real slide, `3.99 × 0.57` of it. Reason
off the ghtml numbers and you will "discover" elements hanging off the canvas that are fine, and
miss the overlaps that are not.

```bash
meta google.slides get --id="$DECK" --output=raw-json > /tmp/deck.json
# rendered box = size.width * transform.scaleX , size.height * transform.scaleY
#                offset by transform.translateX / translateY   (EMU; 12700 EMU = 1pt)
```

With that you can check the whole deck at once instead of eyeballing it — compute each element's
rectangle and assert no text box intersects an image. That catches the failure above in one pass.
**`google.slides lint` will not**: it checks palette and writing style, not geometry.

Then look at a few anyway:

```bash
meta google.slides.slide thumbnail --id="$DECK" --page-id="$PAGE" --save-to=/tmp/s.png
```

`--save-to` is worth knowing because the CLI fetches the image server-side. The `contentUrl` it also
prints is a `googleusercontent.com` link that a devserver usually **cannot** reach directly — `curl`
fails TLS — and there is generally no `pdftoppm`/`gs` to rasterise the PDF export either, so
`--save-to` is often the only way to actually see a slide.

Two things only a render will tell you, both found this way after the arithmetic said the deck was
clean: text that overflows its box (a three-line legend in a two-line strip), and a **figure whose
own caption contradicts the slide title** because the title was corrected and the figure was not.

**Set the type scale explicitly instead of inheriting it.** Font size on a placeholder is inherited
from the layout, and a deck that mixes `28_Text` with `52_Points (Three)` renders two titles of the
same length at visibly different sizes — which also makes any fixed box height wrong for half the
slides. `google.slides.slide set-layout` cannot help: reassigning a slide's layout is unsupported by
the API. Pin the sizes instead, in one batch, and derive box heights from the sizes you chose:

```bash
meta google.slides.content batch --id="$DECK" --ops='[
  {"op":"format-text","element-id":"slide_x_title","font-size":40},
  {"op":"format-text","element-id":"slide_x_body","font-size":20}]'
```

**To set absolute geometry you must drop to the raw API.** `content move` is a *relative* `--dx/--dy`
and `content resize` is a *uniform* `--scale-percent`; neither can reshape a 1164 × 67 title into a
1200 × 76 one. Use `updatePageElementTransform` with `applyMode: ABSOLUTE`, where
`scaleX = target_width_EMU / size.width`:

```bash
meta google.slides.advanced batch-update --id="$DECK" --requests='[
  {"updatePageElementTransform":{"objectId":"slide_x_title","applyMode":"ABSOLUTE",
   "transform":{"scaleX":5.08,"scaleY":0.34,"translateX":1524000,"translateY":1524000,"unit":"EMU"}}}]'
```

One `batch-update` is one write against the 60/minute limit however many requests it carries, so
reflowing a whole deck costs one call, not eighty.

Render figkit output at the aspect ratio you will place it at rather than scaling a doc-shaped
14 × 6.5 figure into a slide.

## Speaker notes

```bash
meta google.slides.slide set-notes --id="$DECK" --page-id="$PAGE" --text='Pause on the Q3 number'
```

Replaces existing notes and locates the notes shape itself. Notes also round-trip in ghtml as
`<aside class="speaker-notes" data-object-id="i3">…</aside>`, but whether editing that `<aside>`
and applying writes them back is INFERRED — `apply` is documented as updating text per element, and
`slide copy-to` explicitly does not carry notes. Use `set-notes`.

## Text, format, tables — and the rate limit

```bash
meta google.slides.content insert-text --id="$DECK" --element-id="$EID" --text='…' --index=0 [--markdown|--html]
meta google.slides.content find-replace --id="$DECK" --find=PLACEHOLDER --replace=Real --match-case
meta google.slides.format format-text --id="$DECK" --element-id="$EID" --bold --font-size=28 --color=ACCENT1 --start=0 --end=9
meta google.slides.format format-paragraph --id="$DECK" --element-id="$EID" --alignment=CENTER --bullets=BULLET_DISC_CIRCLE_SQUARE
meta google.slides.content add-table --id="$DECK" --page-id="$PAGE" --rows=4 --cols=3 --x=40 --y=120 --width=600 --height=200
```

Element commands take `--element-id`, not `--page-id`; `--page-id` on them is an optional guard that
refuses the edit if the element is not on that slide. For tables, `--element-id` is the table's
object ID and `--row`/`--column` (0-based) pick the cell — `insert-text`/`format-text`/
`format-paragraph` **fail** on a bare table id, because a table has no text of its own.
`content move --dx/--dy` and `content resize --scale-percent` are both relative; neither sets an
absolute box.

**60 write requests per minute per user, and a `batchUpdate` of any size counts as one.** A
twenty-edit slide built as twenty commands earns 429s. Compile them:

```bash
meta google.slides.content batch --id="$DECK" --ops=file:///tmp/ops.json --dry-run
```

Ops are the same actions minus leading dashes: `add-textbox, add-shape, add-table, add-line,
add-image, insert-text, format-text, format-paragraph, set-shape-properties, set-background,
find-replace, delete-element, move, resize`. Every create op accepts `"object-id"` so a later op can
address what an earlier one made — but an id under 5 characters is silently swapped for one Google
accepts, so do not assume yours survived. The batch is atomic: one bad op rejects all, and
`requests[N]` maps to `ops[N]` only when every prior op compiled to exactly one request. `batch`'s
`add-image` takes `image-url` only; local files need `content add-image`.

## Share

```bash
meta google.slides.share list  --id="$DECK" --output=json     # id, email, role, type, displayName
meta google.slides.share grant --id="$DECK" --domain --role=commenter
meta google.slides.share grant --id="$DECK" --emails=a@meta.com,b@meta.com --role=writer --notify
```

`--domain` is a **boolean flag** here too — `--domain=meta.com` errors. `--emails` is required
unless `--domain`. Roles: `reader, commenter, writer, owner` (default `reader`). No notification
email goes out without `--notify`. `share` is an alias for `google.drive.share`.

`meta google.slides --detailed-help` prints the example as `meta google.slide.share` (singular).
The singular form resolves, but write `google.slides.share`.

Stay away from `share remove`: `HIGH` / `HUMAN_MUST_CONFIRM`, and it demands both `--yes-i-am-sure`
and `--token=<2FA>`.

## Deep-link a slide

The CLI only ever emits presentation-level URLs
(`meta google.slides list --columns=url` → `https://docs.google.com/presentation/d/<ID>/edit?usp=drivesdk`).
Nothing in any help text documents a slide fragment.

- One slide (INFERRED, standard Google form):
  `https://docs.google.com/presentation/d/<ID>/edit#slide=id.<pageObjectId>`
- Present mode (INFERRED): `https://docs.google.com/presentation/d/<ID>/present#slide=id.<pageObjectId>`
- Presenter / speaker-notes view: do not guess a `/presentnotes` or `?rm=presenter` URL. To read
  notes programmatically use `meta google.slides get --id="$DECK" --page-id="$PAGE"`.

`<pageObjectId>` is CLI-verified and comes from `slide list --output=json`, the `get` summary rows,
the ghtml marker `<!-- gslides:slide:N "<page-id>" -->`, or a comment anchor's page field.

## Read comments back

```bash
meta google.slides.comment list --id="$DECK" --output=json -l 200
meta google.slides.comment list --id="$DECK" --page-id="$PAGE" --include-resolved
meta google.slides.comment list --id="$DECK" --orphaned
meta google.slides.comment reply --id="$DECK" --comment-id="$CID" --content="$(cat /tmp/reply.txt)"
```

Actions: `add, get, list, reply, resolve, reopen, update, delete`. There is no `reply-list` —
replies come back inside `list`, each comment row followed by its reply rows. The same tolerant
parsing and the same thread-grouping logic as [gdoc-cli.md](gdoc-cli.md) apply; nothing about
detecting *which thread needs an answer* changes between Docs and Slides.

**The default `--limit` is 10, and it counts threads, not rows**, so returned row count exceeds it.
`--page-token` is not accepted; the whole read happens server-side and the limit is applied after.

`list` joins each `anchorId` to the page and object recorded in `slide.commentAnchors`, so a sweeper
can route feedback to a slide. Documented anchor fields: page, object, `start_index`/`end_index`
(shape text), `row_index`/`column_index` (table cells), an `anchors` column holding every raw anchor
as JSON, and an `orphaned` marker for anchors whose target was deleted. `--orphaned` cannot combine
with `--page-id`. **`--page-id` omits unanchored legacy Drive comments** — they belong to the file,
not a page, so a page-scoped sweep misses them; do a whole-deck `list` before concluding a deck is
quiet.

`comment add` anchors with `--object-id` (slide page *or* element), plus either `--anchor-text` +
`--occurrence` or explicit UTF-16 `--start-index`/`--end-index`. Without `--object-id` you get a
legacy Drive comment and `--quoted-text` is metadata only — no visible editor anchor. A bare
`@unixname` in `--content` resolves to a real mention token; comments are the only way to notify
anyone about a deck.

## Risk annotations

| command | mutation_risk_level | confirmation | control |
|---|---|---|---|
| `google.slides create` | LOW | AUTONOMOUS | AUTONOMOUS |
| `google.slides apply` | NONE (`operation_type: READ`) | AUTONOMOUS | AUTONOMOUS |
| `google.slides copy` | LOW | AUTONOMOUS | AUTONOMOUS |
| `google.slides replace-image` | LOW | AUTONOMOUS | AUTONOMOUS |
| `google.slides insert-image` / `upload-image` | NONE (`READ`) | AUTONOMOUS | AUTONOMOUS |
| `google.slides.slide add` / `set-notes` / `move` | LOW | AUTONOMOUS | AUTONOMOUS |
| `google.slides.content add-image` / `batch` | MODERATE | AUTONOMOUS | AUTONOMOUS |
| `google.slides delete`, `slide delete` | MODERATE | **HUMAN_MUST_CONFIRM** | AUTONOMOUS |
| `google.slides.share grant` | MODERATE | AUTONOMOUS | AUTONOMOUS |
| `google.slides.share remove` | HIGH | **HUMAN_MUST_CONFIRM** + `--token=<2FA>` | — |

`apply`, `insert-image`, and `upload-image` all report `NONE` / `READ`. **The annotation
understates them** — `apply` overwrites text across the whole deck. Treat all three as writes and do
not rely on the annotation to warn you. Every mutating command accepts `--dry-run`; use it first.

Check anything not in the table before calling it:

```bash
meta metacli.command annotations --command "google.slides.content batch" -o json
```

## Other reads

```bash
meta google.slides get --id="$DECK"                                    # summary, one row per slide
meta google.slides get --id="$DECK" --page-id="$PAGE" --output=json    # that slide's elements + IDs
meta google.slides export --id="$DECK" --export-as=ghtml|pdf|pptx|txt [--as-markdown]
```

`get --output=summary(default)|ghtml|markdown|raw-json|json|yaml`. `--page-id` works on decks too
large to read whole, but single-slide ghtml is read-only — `apply` needs the whole-deck export. The
`.base` snapshot written by `export` is always ghtml regardless of `--export-as`.

## What a real build settled

Most of this file came from `--help`, `describe`, and the `ghtml` reference. One 35-slide deck was
then built against it, which corrected the entries above and closed these:

- `create --from-html` produces one merged text box per slide, drops `<img>`, and renders
  `<aside class="speaker-notes">` as body text. Use `slide add` + `set-notes` + `content add-image`.
- `slide add` / `set-notes` / `content add-image --file` all work as documented and return usable ids.
- `--template=<name>` ships the template's sample gallery as real slides.
- Predefined layout names are often absent from a themed master; resolve `--layout-id` first.
- `move --index` is "insert before the slide currently at index N", not the destination position.
- The `meta` template's slides are 1440 × 810 pt, not 720 × 405.
- `lint` is worth running; it caught only a template-owned colour warning on a clean deck.

## Still not verified

1. Does `create --from-html` also accept the export dialect (`<!-- gslides:slide:N -->`) instead of
   `<hr>`? Moot for deck-building now that `slide add` is the path, but it would matter for a
   round-trip edit.
2. Does `apply` delete a slide that was removed from the local ghtml, or leave it? The docs only
   promise "leaves elements you did not export alone". **This one gates any apply-based update** —
   if apply cannot delete, every removed slide needs an explicit `slide delete`.
3. Does `apply` create a **new slide** for a new `<!-- gslides:slide:N -->` block, or only new
   elements on existing slides? This cookbook assumes only elements.
4. Does editing `<aside class="speaker-notes">` and applying write the notes back? Unknown on the
   *apply* path — it definitely does not work on the *create* path. If it does, a whole deck's notes
   go in one apply instead of one `set-notes` per slide, which matters against the 60-per-minute
   ceiling.
5. Are `data-x/data-y/data-width/data-height` honored on an element that `apply` *creates*, or only
   on ones it updates?
6. Exact JSON key names in `comment list --output=json`. Still open: the one deck available had no
   comments, so the call returned an empty list and printed no keys. The sweep needs the page field
   to route a slide comment to a slide, so settle this the first time a deck gets a comment.
7. The slide-fragment and present-mode URL forms above are the standard Google shapes, not CLI
   output. Click one before putting it in front of a reader. The presenter/notes view URL is a
   complete unknown — do not guess one.
