---
name: humanize
description: Use when prose an agent drafted (a design doc, proposal, report, RCA, README, task description, wiki or Google Doc) reads as AI-generated, or the user says "AI slop", "slop", "sounds like AI", "sounds like ChatGPT", "humanize", "de-slop", or "make it read like a person wrote it". Also use before sharing or publishing an agent-written doc with other people.
---

# humanize

Slop is a shape, not a word list. Asked to "remove the AI slop", an agent strips the bold and the em-dashes and keeps everything else: the same headings, the same length, walls of bullets, and every bold label turned into a one-sentence slogan paragraph. In testing, that pass left two agent-written docs at slop scores of 29-58 (the originals scored 60-69) and changed their prose length by -7 to +10 percent. Rewrites also drop facts: in most test runs, a fresh checker found a reversed decision or an unsupported claim that the writer had reported as "nothing lost". So this skill fixes the facts in a fact sheet first, redrafts to a shape people like to read, and checks every version against the sheet.

## The target shape

The rewrite has these properties. Write toward them; do not edit the original sentence by sentence.

- **An opening paragraph that carries the point.** Two to four sentences: what the doc is for, its conclusion or ask, and who has to act. A reader who stops there has what they need.
- **Visuals wherever the content has a shape.** A flow or state machine becomes a diagram. A trend or comparison becomes a chart. Headline numbers become a small table up top. A risk or decision becomes a callout. `references/visuals.md` says which visual fits which content and how to write it. No visual is decorative.
- **Sections that answer the reader's questions, in the order they arise.** A two-page doc usually needs three to five. Headings are plain noun phrases naming the content ("Retries today", "When the job fails"), never slogans or imperatives.
- **Paragraphs that carry reasoning.** Each makes one point in two to five sentences and joins its facts with "because", "so" and "which". Sentence length varies, the way a person's does. No prose run goes past about 300 words without a visual, table, list or heading.
- **Lists only for parallel items a reader scans:** steps, options, asks. Three or more items, one line each, each starting with its content rather than a bold label.
- **Every reference is a clickable link** with descriptive text: diffs, tasks, SEVs, jobs, `file:line` pointers (to CodeHub), docs and dashboards.
- **Every number has a source** the reader can open: a query, dashboard, job, code pointer or doc.
- **Terms defined where they first appear,** in a clause of the same sentence. Acronyms are spelled out once. Codes and coined labels (stage numbers, priority tags, "-side" phrases) give way to descriptive names.
- **At most one bold phrase per section,** on the one fact a skimmer must not miss.
- **An ending that stops** once the last fact is stated.

With the same facts, the prose ends up at most 5 percent longer than the original, and usually shorter. Mostly-prose docs shrink 20 to 40 percent. Docs dominated by tables, numbers or bullet fragments land between -12 and +3 percent (in testing), because joining fragments into sentences, defining terms inline and captioning figures all add words. Never reach a length target by dropping a fact.

If the doc is a runbook, checklist or reference table, keep its lists and tables and apply only the transforms below.

## The fact sheet

Before redrafting anything, write `facts.md` next to the versions. It is the contract every version is checked against. One fact per line, in this shape:

```
F7 | Three jobs ran at 20K, 20K and 14K rows/s on 10-01, about 3.2M getUnified/min | 20K; 14K; 3.2M; 10-01 | source: https://www.internalfb.com/mast/job/torchx-readypool_0930_ecpm_only_mid-w5mh4shj
F39 | After a severe window the hold doubles per consecutive trip, up to 5 min | doubles; consecutive; 5 min | source: unsourced
```

- **The fact** carries its qualifiers: counts ("six buckets"), orderings ("in priority order"), the reason given for it, and any decision it records ("fix the five rather than adding more").
- **The literals** are the strings that must appear verbatim in every version: numbers, identifiers, names, URLs, and every word in the fact that would change its meaning if dropped ("total", "consecutive", "only", "without also adding", "rather than"). `scripts/fact_check.py` checks them. In testing, every fact a rewrite lost was a dropped qualifier whose literals were only numbers, so the script passed it.
- **The source** is where the fact can be checked. When the original gives none, look for one in the doc's own links, the code, or the query behind the number. If none exists, write `source: unsourced`, keep the fact, and list it in the final report.
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

Word counts cover prose only: tables, code, images and link targets are left out.

| Score | Seen in testing |
|---|---|
| 60-69 | Agent-written proposals and reports, no cleanup |
| 29-58 | A plain "remove the slop" rewrite, no skill |
| 6-14 | The same docs after this skill |
| 11-18 | Hand-written fbcode reference docs |

The target for a proposal or report is 15 or below. The score sees surface patterns only, so the read-back checks cover what it cannot.

## The pass

Keep everything under `/tmp/humanize/<doc-name>/`: the original as `v0.md`, each pass as `v1.md`, `v2.md` and so on, `facts.md`, and any figure PNGs. For a Google Doc, `v0.md` is the doc fetched with `meta google.docs get --id=<id> --output=markdown`.

1. **Score the original:** `python3 ~/.claude/skills/humanize/scripts/slop_score.py v0.md`.
2. **Write `facts.md`** from the original, as above.
3. **Verify the fact sheet with a fresh agent.** Dispatch an agent (Agent tool) that has not seen your work. Give it `v0.md` and `facts.md`, and ask it to list facts the sheet misses or gets wrong. Fix the sheet. Every later check trusts this sheet, so a gap here goes unnoticed for the rest of the run.
4. **Redraft into the next `vN.md`** from the fact sheet, not the old text. Write the opening paragraph first, then pick sections from the reader's questions, then build each section from its facts, adding the visuals and links the target shape calls for. Working from the sheet is what breaks the old skeleton.
5. **Apply the transforms** below to whatever tells the redraft still carries.
6. **Check the version against the fact sheet, both ways:**
   - `python3 ~/.claude/skills/humanize/scripts/fact_check.py facts.md v1.md ... vN.md` must report every fact intact for `vN.md`.
   - A fresh agent compares `vN.md` with `facts.md`, headings, captions and chart titles included, (if the Agent tool is unavailable, because you are yourself a subagent, do this check yourself by re-reading each fact line against the version, and say so in the report). It lists any fact whose meaning changed (a decision reversed, a qualifier dropped, a reason lost) and any claim in `vN.md` the sheet does not support. In testing, unsupported claims crept in through the opening paragraph, headings and chart titles.
   - Fix every item in `vN.md` before going on.
7. **Score again** with every version so far, and run the read-back checks on `vN.md`.
8. **Run another pass from `vN.md`** while the score is above 15 or a read-back check fails, as long as the last pass improved one of them, and there have been fewer than three passes. Steps 4 to 7 repeat for each pass, including the fact check.
9. **Deliver.**
   - **Local file:** write the final version over the original, with its figures alongside.
   - **Google Doc:** follow the Google Docs section of `references/visuals.md`. Fetch ghtml with `meta google.docs get --id=<id> --output=ghtml --dest=file:///tmp/meta-ghtml-<id>.html`, carry the final version into that file, preview with `meta google.docs apply --id=<id> --from=file:///tmp/meta-ghtml-<id>.html --dry-run`, apply, then read the doc back to confirm every diagram and image rendered.
   - **Report:** the score trajectory as printed, the `fact_check.py` result for each version, any unsourced facts, facts that research showed are now stale (leave the author's wording; say what changed), and anything cut on purpose.

## Transforms

| The draft has | Write instead |
|---|---|
| A bold label opening a bullet or paragraph ("**Hold.** The cap...") | A sentence whose subject is the thing: "After a severe window the controller holds..." |
| A one-sentence slogan paragraph ("Nothing fails the job.") | That claim as the first clause of the paragraph holding its evidence: "Nothing fails the job today: the three-strike limits are defined but never read." |
| A paragraph walking through steps, states or a request path | A diagram, with one sentence saying what it shows |
| Numbers compared in prose ("from 0.29M to 0.14-0.17M per minute") | A chart or table, with the source linked under it |
| A bare `D123…`, `T…`, `S…`, job name or `file.py:123` | A link (see `references/visuals.md`) |
| An announcement ("This contributes in four ways.", "This note covers two things.") | Nothing. Start with the first item. |
| An "X, not Y" frame, or "rather than", "instead of", "would have" against an alternative nobody raised | X alone. Keep Y when the system itself does Y somewhere, when Y is what the thing is supposed to measure or do ("advantage that comes from which requests were shed, not from policy quality"), or when the author is ruling Y out ("fix the existing five rather than adding more"). |
| An aphorism or moral ("more load buys less signal", "a different experiment") | The concrete fact it gestures at, with its number. |
| A slogan heading ("Abstain; never default") | A noun phrase naming the content ("Failed rows"). |
| A goals or summary list that repeats the sections below it | The opening paragraph. |
| A glossary block before the content | Each definition inline, at first use. |
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

Run these on the finished version, not on your memory of writing it.

1. `fact_check.py` reports every fact intact, and the fresh-agent check found nothing left unfixed.
2. The slop score is 15 or below, and each tell `--detail` still lists has been read and is justified.
3. Every diff, task, SEV, job and `file:line` reference is a link to a target the original gives or a lookup confirmed, never a guess or a local path. Every number has a source the reader can open.
4. Each flow, comparison or trend in the content is shown as a visual, and no prose run passes about 300 words.
5. The prose word count (as `slop_score.py` prints it) is at most 5 percent above the original's.
6. Bold spans number no more than the sections. No cross-reference points at a section name or number that no longer exists.
7. Read the opening paragraph alone. It gives the point and the ask.

For a Google Doc, also run `meta google.docs lint --id=<id> --category=writing_style`.
