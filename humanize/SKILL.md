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

When two rows fit, pick by where people will meet the doc: projected or presented is a deck, a feed or inbox is a post, a doc people comment on line by line is a proposal or report. When the user names the type or the destination, that wins. Whatever the type, the doc ends with a Nomenclature appendix (see "Plain names" below); only its form changes. The type goes in the humanize context, next.

## The humanize context

The same draft needs a different rewrite depending on who wrote it, who reads it and what it is for, and none of that can be read off the text reliably. So every doc carries a short context block that this skill writes once, confirms with the user, and keeps in the doc, so the next pass starts from it instead of guessing again. One `key: value` line per field:

```
<!-- humanize-context
type: report
purpose: record why nano_retrieval QPS dropped and get the scorer fix approved
author: Anshul Verma (first person singular)
readers: GR RL team, who know the trainer but not the scorer internals; define scorer terms
destination: Google Doc, commented line by line before the Thursday review
ask: approve the scorer thread-pool fix; owner @anshulverma; by 2026-10-09
tone: direct, engineer to engineer
keep: job IDs inline next to each claim; the "Recommended fix" section
avoid: speculation about other teams' services
confirmed: 2026-10-05 by anshulverma
-->
```

- `type` is a row of the table above. `purpose` is what the doc has to get done: a decision, an approval, a record, an update.
- `author` is whose name the doc goes out under, and in which person (first singular, first plural, impersonal). `readers` says who they are, what they already know, and so which terms need defining.
- `destination` is where people meet the doc. `ask` names the action wanted, its owner and its date, or says `none: record only`.
- `keep` lists what must survive the rewrite: required sections, strings other tools parse, identifiers, citations. It overrides any default in this skill (for example `no Nomenclature appendix`), and a read-back check it overrides counts as passed; say so in the report.
- `avoid` holds anything the author has ruled out. `confirmed` gives the date and who confirmed, or reads `no (guessed)`.

**Where it lives.**

- **A markdown or text file:** the HTML comment above, at the very top. If the file starts with YAML frontmatter, put it straight after the closing `---`, because frontmatter parsers need it on line 1. No line inside the block starts with `#` or `---`, so tools that split a file on headings or separators never see it, and `slop_score.py` and `fact_check.py` ignore the block.
- **A Google Doc:** a comment anchored to the title whose text contains `humanize-context`, resolved so it stays out of reviewers' margins. Add it with `meta google.docs.comment add --quoted-text=<title>` and resolve it with `meta google.docs.comment resolve`. Read it back with `meta google.docs.comment list --id=<doc-id> --no-truncate`, which lists resolved comments too.
- **A Google Slides deck:** a first slide titled "Humanize context (not presented)" with the block as its body. Leave it out of `v0.md` and the scoring, put it back on delivery, and tell the presenter to skip it.
- **No place to keep it** (a chat message, or a post typed straight into Workplace): `/tmp/humanize/<doc-name>/context.md`, with its path in the report.

**Getting it right.** Look for an existing block first. If one is there and confirmed, reuse it; only when the doc now contradicts a field (a new ask, a different audience) propose the change and confirm that one field. If one is there but reads `confirmed: no`, ask the user to confirm it once when someone can answer, and write the answer back into the block where it lives, so the next pass reuses it instead of asking again; when nobody can answer, reuse it as it is. If there is no block, guess every field from the doc, where it lives, its author or commit history, and the conversation. Show the guessed block to the user, with three to five title alternatives in the shape the target shape describes, and ask them to confirm or correct it and pick a title, in one message, before redrafting, because the type and readers decide the whole shape. Show it as a plain bulleted list of `field: value` lines, never wrapped in `<!-- -->`: the terminal's markdown renderer hides HTML comments even inside a fenced block, so the user sees an empty box. Put the list in your text and end the turn on the question; text written just before an AskUserQuestion call is hidden behind its card, so never show the block that way. Fields a caller supplies (a plugin that writes the same kind of doc every time) count as confirmed. When nobody can answer (you are a subagent, or the caller said not to ask), go ahead with the guesses, write `confirmed: no (guessed)`, and list the guessed fields in the report.

## The target shape

This is the shape for a proposal, design doc or report. The rewrite has these properties. Write toward them; do not edit the original sentence by sentence.

- **A short title and a TL;DR at the top.** The title is a Title Case noun phrase of at most about 8 words or 60 characters, led by the doc type in brackets ([RFC] for a proposal or design doc, [RCA], [Report], [Design]) and naming the problem and the system: "[RFC] Handling Overloaded Scoring Service in Nano RL Trainer". It names the topic; the TL;DR carries the conclusion, so the title never holds a full sentence or the whole proposal. Draft three to five alternatives in that shape and offer them with the humanize context for the user to pick; when nobody can answer, use the first. Under it, a TL;DR callout of three to five bullets is the executive view: the problem, the fix, and what the fix guarantees. It reads as one chain: the problem, then the fix introduced as a fix ("To fix this, we propose ..."), one bullet per component of the fix ("Additionally, ..."), then the guarantee led by its intent ("We ensure integrity of training experiments by ..."). Each bullet holds one idea in one or two sentences of everyday words. Sizes, owners, timelines, identifiers, lists of asks and operational details (who can change what, kill switches) belong in the body, not the TL;DR; when the doc needs a decision, the last bullet is at most one short line naming who decides and pointing at the asks section. A reader who stops there knows what went wrong and what is proposed, so it replaces a separate opening paragraph. `references/tldr-example.md` shows a TL;DR its author rewrote, and why.
- **A line of reasoning the reader can follow.** Every TL;DR bullet, section opening and paragraph opening says how it relates to what came before: the fix to the problem ("To fix this ..."), a consequence ("Because of that ..."), a limit ("This leaves ..."), a next question ("That raises ..."). In testing, a TL;DR that stated the problem and then opened the next bullet with the mechanism ("Total load has a hard cap ...") read as two unrelated facts, even though every fact was right.
- **Plain names for things.** Each system, call and component is named by what it does ("score request", "scoring service", "AdFinder request"), never by its RPC, class, tier or config name. Units follow the plain name: "AdFinder requests/min", not "getUnified/min". The real identifiers appear only in a Nomenclature table in the appendix (plain name, real name, what it is), in code pointers, and in tables of literal strings such as error markers. Every plain name the body uses has a Nomenclature row. Every doc gets this appendix, whatever its type and readers, with a row for each identifier the original used.
- **Visuals wherever the content has a shape, designed rather than default.** A flow or architecture becomes a styled card diagram with short labels and numbered markers. A rule that changes a value over time becomes an annotated illustration of that value. A trend or comparison becomes a chart. Headline numbers become a small table up top. A risk or decision becomes a callout. `references/visuals.md` says which visual fits which content and how to write it. No visual is decorative.
- **Each section makes one point, with only the facts that carry it.** Before writing a section, state its point in one sentence, then keep the facts the reader needs to understand or believe that point. Implementation qualifiers, corner cases and averages ("only uncached ones when the cache is on", "picked by hashing the user", "about 12.4 on average") move to the appendix when someone implementing the change needs them, and otherwise go. In testing, the author cut exactly these from an overview section that every check had passed.
- **No answers to questions the reader was never led to ask.** A conclusion, rebuttal or piece of evidence needs its question set up first, in the text the reader has already read ("AdFinder scores each ad separately, so you might expect one request per ad. It is one per row: ..."). If readers of this doc would not ask it, cut it. These usually come from a question someone asked the writer during drafting, not from the doc's own argument. In testing, the author flagged "..., so it can't be sending one request per ad" for exactly this.
- **Sections that answer the reader's questions, in the order they arise.** A two-page doc usually needs three to five. Headings are plain noun phrases naming the content ("Retries today", "When the job fails"), never slogans or imperatives.
- **Paragraphs that carry reasoning, in short sentences.** Each paragraph makes one point in two to five sentences. Each sentence carries one idea, sentences average about 15 words, and few pass 25. Join two facts with "because" or "so" when one causes the other, but never stack a third clause or an aside onto the same sentence. A definition never rides as a parenthetical inside a sentence doing other work; it gets a short sentence of its own at first use, or only a Nomenclature row (see the terms rule below). In testing, the author flagged "Rows wait in the trainer's waiting pool until their score arrives, and GRPO, the RL loss, then trains each beam (one candidate output) on its reward relative to the other beams for the same user" as a sentence no person writes. Sentence length varies, the way a person's does. No prose run goes past about 300 words without a visual, table, list or heading.
- **Bullets where the items stand apart, paragraphs where they build on each other.** A list fits items a reader scans or comments on one at a time: steps, options, asks, rules, findings. It reads well when a sentence before it says what the items are, each item makes one distinct point (a line or two), the items run in an order that flows, and each starts with its content rather than a bold label. When one item explains, causes or qualifies the next, that is reasoning, and it goes in a paragraph. Separate defects, mechanisms or stages that reviewers will discuss one by one stay a list even when each needs two sentences, with the reasoning that ties them together in the sentence before or after. A paragraph holding several such items, or one bold sentence in the middle of a paragraph, is a list that got flattened. Mix the two: a doc that is mostly bullets reads as notes, so lists usually take under about a third of the body.
- **Every reference is a clickable link** with descriptive text: diffs, tasks, SEVs, jobs, `file:line` pointers (to CodeHub), docs and dashboards.
- **Every number has a source** the reader can open: a query, dashboard, job, code pointer or doc.
- **Plain spoken English.** Use the everyday verbs an engineer would use with a colleague ("sent", "was capped at", "limits", "stops") over compressing ones ("drew", "budgeted at", "binds", "trips"): "a job capped at 20K rows/s sent about 22.7K score requests/s", not "a job budgeted at 20K rows/s drew about 22.7K score requests/s". Compact notation people write every day stays: slash units (rows/s, requests/min) and K/M numbers (22.7K, 3.2M). Keep to about one number per clause, so a sentence never reads as a row of a spreadsheet.
- **Terms defined only for the readers who need it, where they first appear.** Define a term in the body only when the `readers` field says they do not know it; a term they know gets only its Nomenclature row. A body definition comes at or before the term's first use and says what the paragraph needs from it. A definition sentence tacked on after the term has already been used, or one the paragraph never builds on, gets cut: in testing, splitting a parenthetical left "A beam is one candidate output." at the end of a paragraph that had used "beam" twice, for readers who work with beams daily, and the author could not tell why it was there. Acronyms are spelled out once. Codes and coined labels (stage numbers, priority tags, "-side" phrases) give way to descriptive names.
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
- **No title block, TL;DR callout, headings, tables or figures.** Feeds and chat render headings and tables badly, and the linked doc carries the detail. A chart goes in only when the chart is the news, and then from real data.
- **The team's own terms,** because the readers are the team. Define only what an outside reader of that group would not know.
- **Links on any diff, task or SEV the post names,** and the link to the full doc in the closing ask.
- **It ends on the ask**, with the owner (@name) and the date, one line per ask when there are two. At most a one-word thanks after it.
- **Then a Nomenclature list,** one line per name ("score request: `genScorePreselectedAds`, the call that prices one rollout row"), as a list because feeds render tables badly.

The length rule applies. The prose slop score works for a post, with a target of 15 or below. Read-back checks 1 to 3 and 6 apply, plus these: the first line alone says the news or the ask, the body is at most 250 words, and nothing in it would render badly in the destination (no headings, tables or callouts).

## Runbooks and references

Keep a runbook's numbered steps, a checklist's items and a reference's tables, and apply the transforms only to the prose around them. Commands, flags and config keys stay verbatim in fenced blocks or backticks: they are the content, so the plain-names rule does not reach them. The Nomenclature appendix still maps every plain name the prose uses. The slop score's list, heading and one-sentence-paragraph components measure the structure this kind of doc needs, so read the tells in `--detail` and fix those instead of chasing the total.

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
- **A fact the author cuts stays on the sheet, marked.** Prefix its line with `cut ` ("cut F112 | ...") and note who cut it in the source column. `fact_check.py` skips cut lines and reports how many there are, so a deliberate cut never reads as a loss and a silent loss never hides as a cut. A detail moved to the appendix is not cut: it stays a normal fact, satisfied by the appendix.
- **A value nobody has confirmed stays out of the doc and its figures.** A number that someone assumed, derived or proposed for a thing another team owns (a quota, a threshold, a launch date) is not a fact until its owner sets it, even when the author said to assume it. Prefix its line with `assumed ` and say in the source column what would confirm it. The doc names the thing without the number, keeps the evidence a reader would use to pick it, and turns the value into an ask or an open question. Re-justify anything derived from it from confirmed facts, or mark it assumed too. Pass the figure sources with `--figures`: `fact_check.py` fails any version or figure that still holds an assumed literal. In testing, a quota of "about 9K requests/s", derived from an RCA optimum and assumed by the author, sat in the TL;DR, a section, an ask, a diagram and a chart, and sized another limit, while the quota's landed config read 50 requests/s in dry-run; the author asked to remove it once they noticed it was unconfirmed.

## The slop score

`scripts/slop_score.py` gives each version a score from 0 (clean) to 100 (all slop), normalised per 1,000 words. It weighs AI tells, bold density, list share, one-sentence paragraphs, sentence-length uniformity, long sentences, heading density, unlinked references and walls of text. Pass it the versions in order, and it prints the trajectory; `--detail` shows the components:

```
pass    slop  change  words  vs orig  file
orig      69           1455           v0.md
v1         8     -61   1294     -11%  v1.md
v2         9     -60   1280     -12%  v2.md
v3         6     -63   1291     -11%  v3.md
```

Word counts cover body prose only: the TL;DR, the Nomenclature appendix, tables, code, images and link targets are left out. For a slide deck, pass `--type slides`, which scores on-slide words, titles, visuals and notes instead (see `references/slides.md`).

| Score | Seen in testing |
|---|---|
| 53-66 | Agent-written proposals and reports, no cleanup |
| 30-52 | A plain "remove the slop" rewrite, no skill |
| 10-19 | The same docs after this skill, before the short-sentence rule |
| 9-20 | Hand-written fbcode reference docs |

The target for a proposal or report is 15 or below. The score sees surface patterns only, so the read-back checks cover what it cannot.

## The pass

Keep everything under `/tmp/humanize/<doc-name>/`: the original as `v0.md`, each pass as `v1.md`, `v2.md` and so on, `facts.md`, and any figure PNGs. For a Google Doc, `v0.md` is the doc fetched with `meta google.docs get --id=<id> --output=markdown`.

1. **Settle the humanize context** (find it, or guess it and confirm it), which fixes the doc type. Copy the block to the top of `facts.md`. Then **score the original:** `python3 ~/.claude/skills/humanize/scripts/slop_score.py v0.md` (add `--type slides` for a deck).
2. **Write `facts.md`** from the original, as above, under the context block.
3. **Verify the fact sheet with a fresh agent.** Dispatch an agent (Agent tool) that has not seen your work (if you are yourself a subagent and cannot, do this and the step 6 and 7 checks yourself, and say so in the report). Give it `v0.md` and `facts.md`, and ask it to list facts the sheet misses or gets wrong. Fix the sheet. Every later check trusts this sheet, so a gap here goes unnoticed for the rest of the run.
4. **Redraft into the next `vN.md`** from the fact sheet, not the old text, toward the shape for the doc's type. Pick the plain names first and write the Nomenclature appendix, whatever the type. For a proposal or report, then write the title and TL;DR, then pick sections from the reader's questions, then build each section from its facts, adding the visuals and links the target shape calls for. Working from the sheet is what breaks the old skeleton.
5. **Apply the transforms** below to whatever tells the redraft still carries.
6. **Check the version against the fact sheet, both ways:**
   - `python3 ~/.claude/skills/humanize/scripts/fact_check.py facts.md v1.md ... vN.md` must report every fact intact for `vN.md`.
   - A fresh agent compares `vN.md` with `facts.md`, headings, captions and chart titles included. It lists any fact whose meaning changed (a decision reversed, a qualifier dropped, a reason lost) and any claim in `vN.md` the sheet does not support. In testing, unsupported claims crept in through the opening paragraph, headings and chart titles.
   - Fix every item in `vN.md` before going on.
7. **Read every sentence with a fresh agent.** Give it `vN.md`, the humanize context and the plain-English rules (the transforms table), and ask it to go through the whole doc, sentence by sentence, as one of the `readers`. It lists every sentence that reader would stumble on, with a rewrite that keeps the sentence's fact-sheet literals:
   - an idiom or jargon verb standing in for a mechanism ("failed fast", "ran at its full budget", "retries overload"): say what happened ("each failed request came back in milliseconds, so the trainer sent the next one at once");
   - a causal link the reader has to supply;
   - a term or label used before the doc says what it means, or never explained, for the `readers` ("Degraded responses also count as scored." before the doc says these are empty or partial responses): lead with the concrete thing, and drop the label or give it afterwards;
   - a word for an internal part of a system the readers do not own ("ranking shards", "in-band drops", tier or service component names), even a plain-sounding one: it reads as a smoke screen. Say the effect on the readers' system instead ("AdFinder skipped half of the servers that score ads, so those ads came back with no value"), and keep the part's name only in the Nomenclature appendix;
   - a detail that does not serve its paragraph's point, which moves to the appendix or is cut ("...and the three-strike limits are defined but never read" in a paragraph whose point is that failed batches are dropped).

   The tells the score counts are a floor: in testing, a doc at score 8 still had all of these, because a word list cannot read. Review the list, apply what holds, and fact-check again. **When the user flags one sentence, treat it as a sample:** fix it, add the pattern to this skill, then rerun this read on the whole doc for that pattern, never only on the flagged sentence.
8. **Score again** with every version so far, and run the read-back checks on `vN.md`.
9. **Run another pass from `vN.md`** while the score is above 15, a read-back check fails or the sentence read finds anything, as long as the last pass improved one of them, and there have been fewer than three passes. Steps 4 to 8 repeat for each pass, including the fact check.
10. **Deliver.**
   - **Local file:** write the final version over the original, with its figures alongside and the context block at the top.
   - **Google Slides deck:** follow the delivery section of `references/slides.md`, and put the context slide first.
   - **Google Doc:** follow the Google Docs section of `references/visuals.md`. Fetch ghtml with `meta google.docs get --id=<id> --output=ghtml --dest=file:///tmp/meta-ghtml-<id>.html`, carry the final version into that file, preview with `meta google.docs apply --id=<id> --from=file:///tmp/meta-ghtml-<id>.html --dry-run`, apply, then read the doc back to confirm every diagram and image rendered. Add or update the resolved context comment.
   - **Report:** the context block and any field still guessed, the score trajectory as printed, the `fact_check.py` result for each version, any unsourced facts, facts that research showed are now stale (leave the author's wording; say what changed), and anything cut on purpose.

## Transforms

| The draft has | Write instead |
|---|---|
| Prose that repeats the table or figure beside it | One of the two. |
| A bold label opening a bullet or paragraph ("**Hold.** The cap...") | The same bullet or sentence led by its subject: "After a severe window the controller holds..." |
| A one-sentence slogan paragraph ("Nothing fails the job.") | That claim as the first clause of the paragraph holding its evidence: "Nothing fails the job today: the three-strike limits are defined but never read." |
| A paragraph walking through steps, states or a request path | A diagram, with one sentence saying what it shows |
| Numbers compared in prose ("from 0.29M to 0.14-0.17M per minute") | A chart or table, with the source linked under it |
| A bare `D123…`, `T…`, `S…`, job name or `file.py:123` | A link (see `references/visuals.md`) |
| A conclusion or rebuttal nothing set up ("..., so it can't be sending one request per ad") | The question set up first, if readers would ask it; otherwise nothing. |
| An announcement ("This contributes in four ways.", "This note covers two things.") | Nothing. Start with the first item. |
| A bullet, section or paragraph that opens on a new topic with no link to the one before (problem, then straight into mechanism) | The same content led by its link: "To fix this, we propose ...", "Because of that ...", "This leaves ..." |
| An "X, not Y" frame, or "rather than", "instead of", "would have" against an alternative nobody raised | X alone. Keep Y when the system itself does Y somewhere, when Y is what the thing is supposed to measure or do ("advantage that comes from which requests were shed, not from policy quality"), or when the author is ruling Y out ("fix the existing five rather than adding more"). |
| An aphorism or moral ("more load buys less signal", "a different experiment") | The concrete fact it gestures at, with its number. |
| A slogan heading ("Abstain; never default") | A noun phrase naming the content ("Failed rows"). |
| A summary list that only repeats the section headings below it | The opening paragraph. A numbered goals or requirements list that later sections cite stays. |
| A qualifier, corner case or average in an overview or a section about something else ("only uncached ones when the cache is on", "picked by hashing the user") | Nothing in that section. The appendix, if someone implementing the change needs it. |
| A glossary block before the content | Each definition inline, at first use, and the identifier in the Nomenclature appendix. |
| An RPC, class, tier, config or metric name in the prose (`getUnified`, `genScorePreselectedAds`, `rl_preselected_ads_scoring`) | The plain name for what it does, with the identifier in the Nomenclature appendix. |
| A hedge clause ("seems to", "appears to", "may potentially") or process narration ("I found", "I can't find") | The fact. If the uncertainty is real, one word: "likely". |
| Signposts and AI vocabulary ("importantly", "notably", "it is worth noting", "delve", "robust", "leverage", "pivotal", "underscore", "foster") | Nothing, or the concrete verb. |
| A run of short sentences of the same length | Two related facts joined by "because" or "so". |
| A sentence over about 25 words, or one carrying two ideas, a stacked definition or an aside | One sentence per idea, with definitions in their own sentence: "Rows wait in the trainer's waiting pool until their score arrives. GRPO, the RL loss, then trains each beam on its reward relative to the other beams for the same user." |
| A triplet kept for rhythm | Only the items that carry a fact. |
| A coined label or stiff verb for something ordinary ("per-job rate gate", "coverage optimum", "expired-rows change", "retires", "lives in", "first-comes-first-serves") | What it does, in the words an engineer would say to a colleague: "today's per-job rate limit", "the load where the most users get fully scored", "the change that gives rows a deadline", "turns off", "sits in", "serves callers first come, first served". |
| A compressing verb ("budgeted at", "drew", "binds", "trips") | The everyday verb: "a job capped at 20K rows/s sent about 22.7K score requests/s". |
| An em or en dash | A colon, a comma, parentheses, or a new sentence. |
| A semicolon welding two claims | Two sentences. |
| A blockquote | Quotation marks inline, or a fenced block for text meant to be pasted. |

## What stays

Every fact on the sheet, real uncertainty, and the author's decisions, conclusions and asks, at the strength the author gave them. Add no new claims, including in the opening paragraph: each sentence there summarises something the body says. New data is allowed only when it comes from a source the original cites (a data point for a chart, say), and it goes onto the fact sheet, with that source, before it goes into a version. When a list of steps or a data table carries the content better than prose, it stays.

## Read-back checks

Run these on the finished version, not on your memory of writing it. They are written for a proposal or report. A deck replaces checks 4, 5, 7 and 8 with the checks in `references/slides.md`; a post or update keeps 1 to 3 and 6 and adds its own checks above. Every type, deck and post included, ends with a Nomenclature appendix that has a row for every plain name it uses and every identifier the original used.

1. `fact_check.py` reports every fact intact, and the fresh-agent check found nothing left unfixed.
2. The slop score is 15 or below, and each tell `--detail` still lists has been read and is justified.
3. Every diff, task, SEV, job and `file:line` reference is a link to a target the original gives or a lookup confirmed, never a guess or a local path. Every number has a source the reader can open.
4. Each flow, comparison or trend in the content is shown as a visual, and no prose run passes about 300 words. No diagram box carries more than about 4 words or any arrow more than 3, and every figure was rendered and looked at before use.
5. The prose word count (as `slop_score.py` prints it) is at most 5 percent above the original's.
6. Each section's first sentence states its point, and every other sentence in it supports that point. Bold spans number no more than the sections. No cross-reference points at a section name or number that no longer exists.
7. The title is at most about 8 words or 60 characters, starts with the bracketed doc type, and is a noun phrase, not a sentence. Read the title and TL;DR alone. They give the problem, the fix and what it guarantees, each bullet holds one idea and follows from the one before (the fix is introduced as the fix to the stated problem), and no bullet carries a size, owner, identifier, list of asks or operational detail. Then read only the first sentence of each section in order: they should tell the same story without gaps.
8. Every sentence `slop_score.py --detail` lists as a long sentence is split or rewritten, in list items and spec rules as much as in paragraphs; the score only penalises a share above 15%, so a passing score does not mean this check passed. No sentence stacks a definition or aside onto a sentence doing other work, and every body definition is of a term the `readers` field says they do not know, placed at or before its first use. No prose sentence uses a compressing verb (`slop_score.py --detail` counts them); slash units and K/M numbers are fine. No raw identifier remains in the body outside code pointers, literal-string tables and the Nomenclature appendix (`slop_score.py --detail` lists them), and every plain name has a Nomenclature row.

For a Google Doc, also run `meta google.docs lint --id=<id> --category=writing_style`.
