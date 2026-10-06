---
name: humanize
description: Use when prose an agent drafted (a design doc, proposal, report, RCA, slide deck, Workplace post, status update, README, task description, wiki, Google Doc or Google Slides deck) reads as AI-generated, or the user says "AI slop", "slop", "sounds like AI", "sounds like ChatGPT", "humanize", "de-slop", or "make it read like a person wrote it". Also use before sharing or publishing an agent-written doc with other people.
---

# humanize

Slop is a shape, not a word list. Asked to "remove the AI slop", an agent strips the bold and the em-dashes and keeps everything else: the same headings, the same length, walls of bullets, and every bold label turned into a one-sentence slogan paragraph. In testing, that pass left two agent-written docs at slop scores of 29-58 (the originals scored 60-69) and changed their prose length by -7 to +10 percent. Rewrites also drop facts: in most test runs, a fresh checker found a reversed decision or an unsupported claim that the writer had reported as "nothing lost". So this skill fixes the facts in a fact sheet first, redrafts to a shape people like to read, and checks every version against the sheet.

## The doc type

The right shape depends on what the doc is and where it is read, so decide that first. In testing, one shape for every doc turned a slide deck into paragraphs under slide titles and a 280-word team post into a mini design doc with headings, tables and a glossary. Both scored clean, and readers judged both the wrong shape.

| The doc is | Signals | Its shape |
|---|---|---|
| A proposal, design doc or RFC | Asks for a decision; goals, design, alternatives, open questions | The target shape below |
| A report, RCA or investigation | Findings, measurements, a timeline, what happened and why | The target shape below, with the report changes |
| A slide deck | Slides with titles and speaker notes, `---` between slides, a Google Slides link, "deck", "slides", "presentation" | `references/slides.md` |
| A post, status update, announcement or email | Under about 400 words, a greeting or sign-off, @mentions, a feed or inbox as its destination | Posts and updates, below |
| A runbook, checklist, reference or README | Numbered steps, commands, flags, tables of values | Runbooks and references, below |
| A task or bug description | A task ID or template; problem, repro, expected behaviour | Posts and updates, plus a "done when" line |

When two rows fit, pick by where people will meet the doc: projected or presented is a deck, a feed or inbox is a post, a doc people comment on line by line is a proposal or report. When the user names the type or the destination, that wins. Write the type and the readers at the top of `facts.md` (`type: slide deck | readers: GR RL team, presented live`), because the readers decide which terms need defining.

## The target shape

This is the shape for a proposal, design doc or report. The rewrite has these properties. Write toward them; do not edit the original sentence by sentence.

- **A title and a TL;DR at the top.** The title says in plain words what the doc decides or proposes, and a proposal's title says it is one ("Proposal: ..."). Under it, a TL;DR callout of three to five one-line bullets gives the problem, the proposal, and the ask with who has to act. A reader who stops there has what they need, so it replaces a separate opening paragraph.
- **Plain names for things.** Each system, call and component is named by what it does ("score request", "scoring service", "AdFinder request"), never by its RPC, class, tier or config name. Units follow the plain name: "AdFinder requests/min", not "getUnified/min". The real identifiers appear only in a Nomenclature table in the appendix (plain name, real name, what it is), in code pointers, and in tables of literal strings such as error markers. Every plain name the body uses has a Nomenclature row.
- **Visuals wherever the content has a shape, designed rather than default.** A flow or architecture becomes a styled card diagram with short labels and numbered markers. A rule that changes a value over time becomes an annotated illustration of that value. A trend or comparison becomes a chart. Headline numbers become a small table up top. A risk or decision becomes a callout. `references/visuals.md` says which visual fits which content and how to write it. No visual is decorative.
- **Sections that answer the reader's questions, in the order they arise.** A two-page doc usually needs three to five. Headings are plain noun phrases naming the content ("Retries today", "When the job fails"), never slogans or imperatives.
- **Paragraphs that carry reasoning.** Each makes one point in two to five sentences and joins its facts with "because", "so" and "which". Sentence length varies, the way a person's does. No prose run goes past about 300 words without a visual, table, list or heading.
- **Bullets where the items stand apart, paragraphs where they build on each other.** A list fits items a reader scans or comments on one at a time: steps, options, asks, rules, findings. It reads well when a sentence before it says what the items are, each item makes one distinct point (a line or two), the items run in an order that flows, and each starts with its content rather than a bold label. When one item explains, causes or qualifies the next, that is reasoning, and it goes in a paragraph. Separate defects, mechanisms or stages that reviewers will discuss one by one stay a list even when each needs two sentences, with the reasoning that ties them together in the sentence before or after. A paragraph holding several such items, or one bold sentence in the middle of a paragraph, is a list that got flattened. Mix the two: a doc that is mostly bullets reads as notes, so lists usually take under about a third of the body.
- **Every reference is a clickable link** with descriptive text: diffs, tasks, SEVs, jobs, `file:line` pointers (to CodeHub), docs and dashboards.
- **Every number has a source** the reader can open: a query, dashboard, job, code pointer or doc.
- **Terms defined where they first appear,** in a clause of the same sentence. Acronyms are spelled out once. Codes and coined labels (stage numbers, priority tags, "-side" phrases) give way to descriptive names.
- **At most one bold phrase per section,** on the one fact a skimmer must not miss.
- **An ending that stops** once the last fact is stated.
- **Numbered items keep their numbers** when readers will cite them: goals, requirements, design parts, asks, open questions. Reviewers comment "re goal 2", so a numbered list that the sections refer back to stays a numbered list.
- **Spec values in the body.** Thresholds, timings and limits live in the text, a list or a table, and a group of parallel rules stays one rule per line so reviewers can comment on each. A caption describes its figure and never holds the only copy of a rule, and a drawing of a rule obeys the rule as the text states it.
- **Identifiers an ask names stay next to it.** When an ask requests a specific field, flag or exception, its real name appears in the ask beside the plain name, because the owner acts on that name.

In a report or RCA, the TL;DR gives the finding, the evidence it rests on and what happens next. An RCA's timeline becomes a table or chart, and its action items a table with an owner and a task link for each.

With the same facts, the prose ends up at most 5 percent longer than the original, and usually shorter. Mostly-prose docs shrink 20 to 40 percent. Docs dominated by tables, numbers or bullet fragments land between -12 and +3 percent (in testing), because joining fragments into sentences, defining terms inline and captioning figures all add words. Never reach a length target by dropping a fact.

## Posts and updates

A Workplace post, status update, announcement, chat message or email is read in a feed or inbox, often on a phone, by people who already know the project. Its shape:

- **The first line is the news or the ask** in plain words, at most about 12 words, bold when the medium shows a headline: "Scorer load-shedding proposal for nano_retrieval: comments by Friday". No greeting, no "excited to share", no emoji headers.
- **80 to 250 words of body**: two or three short paragraphs, or one paragraph and up to five one-line bullets for parallel items. A bullet may lead with a plain two-word label and a colon ("Hard caps: ..."), never a bold one.
- **No title block, TL;DR callout, headings, tables, Nomenclature appendix or figures.** Feeds and chat render headings and tables badly, and the linked doc carries the detail. A chart goes in only when the chart is the news, and then from real data.
- **The team's own terms,** because the readers are the team. Define only what an outside reader of that group would not know.
- **Links on any diff, task or SEV the post names,** and the link to the full doc in the closing ask.
- **It ends on the ask**, with the owner (@name) and the date, one line per ask when there are two. At most a one-word thanks after it.

The length rule applies. The prose slop score works for a post, with a target of 15 or below. Read-back checks 1 to 3 and 6 apply, plus these: the first line alone says the news or the ask, the body is at most 250 words, and nothing in it would render badly in the destination (no headings, tables or callouts).

## Runbooks and references

Keep a runbook's numbered steps, a checklist's items and a reference's tables, and apply the transforms only to the prose around them. Commands, flags and config keys stay verbatim in fenced blocks or backticks: they are the content, so the plain-names rule does not reach them. The slop score's list, heading and one-sentence-paragraph components measure the structure this kind of doc needs, so read the tells in `--detail` and fix those instead of chasing the total.

## The fact sheet

Before redrafting anything, write `facts.md` next to the versions. It is the contract every version is checked against. One fact per line, in this shape:

```
F7 | Three jobs ran at 20K, 20K and 14K rows/s on 10-01, about 3.2M getUnified/min | 20K; 14K; 3.2M; 10-01 | source: https://www.internalfb.com/mast/job/torchx-readypool_0930_ecpm_only_mid-w5mh4shj
F39 | After a severe window the hold doubles per consecutive trip, up to 5 min | doubles; consecutive; 5 min | source: unsourced
```

- **The fact** carries its qualifiers: counts ("six buckets"), orderings ("in priority order"), the reason given for it, and any decision it records ("fix the five rather than adding more").
- **The literals** are strings copied from the original's wording that must appear verbatim in every version (an identifier that moves out of the prose survives in the Nomenclature table): numbers, identifiers, names, URLs, and every word in the fact that would change its meaning if dropped ("total", "consecutive", "only", "without also adding", "rather than"). `scripts/fact_check.py` checks them. In testing, every fact a rewrite lost was a dropped qualifier whose literals were only numbers, so the script passed it.
- **The source** is where the fact can be checked. When the original gives none, look for one in the doc's own links, the code, or the query behind the number. A decision, plan or ask the author states is its own source: write `source: author`. If a measurement has no source, write exactly `source: unsourced` (the script matches that word alone), keep the fact, and list it in the final report.
- Cover decisions, asks, caveats, open questions and cross-references as facts too.

## The slop score

`scripts/slop_score.py` gives each version a score from 0 (clean) to 100 (all slop), normalised per 1,000 words. It weighs AI tells, bold density, list share, one-sentence paragraphs, sentence-length uniformity, heading density, unlinked references and walls of text. Pass it the versions in order, and it prints the trajectory; `--detail` shows the components:

```
pass    slop  change  words  vs orig  file
orig      69           1455           v0.md
v1         8     -61   1294     -11%  v1.md
v2         9     -60   1280     -12%  v2.md
v3         6     -63   1291     -11%  v3.md
```

Word counts cover body prose only: the TL;DR, tables, code, images and link targets are left out. For a slide deck, pass `--type slides`, which scores on-slide words, titles, visuals and notes instead (see `references/slides.md`).

| Score | Seen in testing |
|---|---|
| 60-69 | Agent-written proposals and reports, no cleanup |
| 29-58 | A plain "remove the slop" rewrite, no skill |
| 6-14 | The same docs after this skill |
| 11-18 | Hand-written fbcode reference docs |

The target for a proposal or report is 15 or below. The score sees surface patterns only, so the read-back checks cover what it cannot.

## The pass

Keep everything under `/tmp/humanize/<doc-name>/`: the original as `v0.md`, each pass as `v1.md`, `v2.md` and so on, `facts.md`, and any figure PNGs. For a Google Doc, `v0.md` is the doc fetched with `meta google.docs get --id=<id> --output=markdown`.

1. **Decide the doc type** from the table above, and **score the original:** `python3 ~/.claude/skills/humanize/scripts/slop_score.py v0.md` (add `--type slides` for a deck).
2. **Write `facts.md`** from the original, as above, with the type and readers at the top.
3. **Verify the fact sheet with a fresh agent.** Dispatch an agent (Agent tool) that has not seen your work (if you are yourself a subagent and cannot, do this and the step 6 check yourself, and say so in the report). Give it `v0.md` and `facts.md`, and ask it to list facts the sheet misses or gets wrong. Fix the sheet. Every later check trusts this sheet, so a gap here goes unnoticed for the rest of the run.
4. **Redraft into the next `vN.md`** from the fact sheet, not the old text, toward the shape for the doc's type. For a proposal or report, pick the plain names first and write the Nomenclature table, then the title and TL;DR, then pick sections from the reader's questions, then build each section from its facts, adding the visuals and links the target shape calls for. Working from the sheet is what breaks the old skeleton.
5. **Apply the transforms** below to whatever tells the redraft still carries.
6. **Check the version against the fact sheet, both ways:**
   - `python3 ~/.claude/skills/humanize/scripts/fact_check.py facts.md v1.md ... vN.md` must report every fact intact for `vN.md`.
   - A fresh agent compares `vN.md` with `facts.md`, headings, captions and chart titles included. It lists any fact whose meaning changed (a decision reversed, a qualifier dropped, a reason lost) and any claim in `vN.md` the sheet does not support. In testing, unsupported claims crept in through the opening paragraph, headings and chart titles.
   - Fix every item in `vN.md` before going on.
7. **Score again** with every version so far, and run the read-back checks on `vN.md`.
8. **Run another pass from `vN.md`** while the score is above 15 or a read-back check fails, as long as the last pass improved one of them, and there have been fewer than three passes. Steps 4 to 7 repeat for each pass, including the fact check.
9. **Deliver.**
   - **Local file:** write the final version over the original, with its figures alongside.
   - **Google Slides deck:** follow the delivery section of `references/slides.md`.
   - **Google Doc:** follow the Google Docs section of `references/visuals.md`. Fetch ghtml with `meta google.docs get --id=<id> --output=ghtml --dest=file:///tmp/meta-ghtml-<id>.html`, carry the final version into that file, preview with `meta google.docs apply --id=<id> --from=file:///tmp/meta-ghtml-<id>.html --dry-run`, apply, then read the doc back to confirm every diagram and image rendered.
   - **Report:** the score trajectory as printed, the `fact_check.py` result for each version, any unsourced facts, facts that research showed are now stale (leave the author's wording; say what changed), and anything cut on purpose.

## Transforms

| The draft has | Write instead |
|---|---|
| Prose that repeats the table or figure beside it | One of the two. |
| A bold label opening a bullet or paragraph ("**Hold.** The cap...") | The same bullet or sentence led by its subject: "After a severe window the controller holds..." |
| A one-sentence slogan paragraph ("Nothing fails the job.") | That claim as the first clause of the paragraph holding its evidence: "Nothing fails the job today: the three-strike limits are defined but never read." |
| A paragraph walking through steps, states or a request path | A diagram, with one sentence saying what it shows |
| Numbers compared in prose ("from 0.29M to 0.14-0.17M per minute") | A chart or table, with the source linked under it |
| A bare `D123…`, `T…`, `S…`, job name or `file.py:123` | A link (see `references/visuals.md`) |
| An announcement ("This contributes in four ways.", "This note covers two things.") | Nothing. Start with the first item. |
| An "X, not Y" frame, or "rather than", "instead of", "would have" against an alternative nobody raised | X alone. Keep Y when the system itself does Y somewhere, when Y is what the thing is supposed to measure or do ("advantage that comes from which requests were shed, not from policy quality"), or when the author is ruling Y out ("fix the existing five rather than adding more"). |
| An aphorism or moral ("more load buys less signal", "a different experiment") | The concrete fact it gestures at, with its number. |
| A slogan heading ("Abstain; never default") | A noun phrase naming the content ("Failed rows"). |
| A summary list that only repeats the section headings below it | The opening paragraph. A numbered goals or requirements list that later sections cite stays. |
| A glossary block before the content | Each definition inline, at first use, and the identifier in the Nomenclature appendix. |
| An RPC, class, tier, config or metric name in the prose (`getUnified`, `genScorePreselectedAds`, `rl_preselected_ads_scoring`) | The plain name for what it does, with the identifier in the Nomenclature appendix. |
| A hedge clause ("seems to", "appears to", "may potentially") or process narration ("I found", "I can't find") | The fact. If the uncertainty is real, one word: "likely". |
| Signposts and AI vocabulary ("importantly", "notably", "it is worth noting", "delve", "robust", "leverage", "pivotal", "underscore", "foster") | Nothing, or the concrete verb. |
| A run of short sentences of the same length | Related facts joined by "because", "so" or "which". |
| A triplet kept for rhythm | Only the items that carry a fact. |
| An em or en dash | A colon, a comma, parentheses, or a new sentence. |
| A semicolon welding two claims | Two sentences. |
| A blockquote | Quotation marks inline, or a fenced block for text meant to be pasted. |

## What stays

Every fact on the sheet, real uncertainty, and the author's decisions, conclusions and asks, at the strength the author gave them. Add no new claims, including in the opening paragraph: each sentence there summarises something the body says. New data is allowed only when it comes from a source the original cites (a data point for a chart, say), and it goes onto the fact sheet, with that source, before it goes into a version. When a list of steps or a data table carries the content better than prose, it stays.

## Read-back checks

Run these on the finished version, not on your memory of writing it. They are written for a proposal or report. A deck replaces checks 4, 5, 7 and 8 with the checks in `references/slides.md`; a post or update keeps 1 to 3 and 6 and adds its own checks above.

1. `fact_check.py` reports every fact intact, and the fresh-agent check found nothing left unfixed.
2. The slop score is 15 or below, and each tell `--detail` still lists has been read and is justified.
3. Every diff, task, SEV, job and `file:line` reference is a link to a target the original gives or a lookup confirmed, never a guess or a local path. Every number has a source the reader can open.
4. Each flow, comparison or trend in the content is shown as a visual, and no prose run passes about 300 words. No diagram box carries more than about 4 words or any arrow more than 3, and every figure was rendered and looked at before use.
5. The prose word count (as `slop_score.py` prints it) is at most 5 percent above the original's.
6. Bold spans number no more than the sections. No cross-reference points at a section name or number that no longer exists.
7. Read the title and TL;DR alone. They give the problem, the proposal and the ask.
8. No raw identifier remains in the body outside code pointers, literal-string tables and the Nomenclature appendix (`slop_score.py --detail` lists them), and every plain name has a Nomenclature row.

For a Google Doc, also run `meta google.docs lint --id=<id> --category=writing_style`.
