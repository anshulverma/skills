# Counter-metrics

The slop score falls when a pass cuts, simplifies or rephrases, and each of those can quietly cost the doc a fact, add a claim, or make it harder to understand. These metrics catch that. Run them on the original and on every version, and print them with `scripts/metrics.py` next to the slop trajectory.

| Metric | Catches | Target | Kind |
|---|---|---|---|
| Fact retention (literals) | a dropped number, name or qualifier | 100% | gate |
| Fact meaning kept | a fact whose literals survived but whose meaning changed | 100% | gate |
| Factual precision | a claim the fact sheet does not support | 100% | gate |
| Cold-read comprehension | a doc cut or compressed past understanding | 90% or more | target |
| TL;DR-only comprehension | a TL;DR that does not stand alone | 100% | target |
| Unknown terms | a term used but never made clear | 0 | target |
| Length vs target | bloat | 1.00 or less | target |
| Author rewrite share | how much of a delivered version the author rewrote | falls over time | trend |

A version that fails a gate is not delivered. A pass may not improve one target by making another worse; when it does, keep the better version.

Each agent below is fresh: it has not seen the drafting, the other agents' output or earlier versions. Paste the doc text into the prompt; do not give it a path. Keep each agent's output to the JSON shown, so payloads stay small. Save each result next to the versions (`quiz.json`, `audit-vN.json`, `graded-vN.json`).

## Quiz (once per doc)

Generated from the fact sheet, not the doc, so it measures whether the doc conveys what it must, and reused unchanged for every version so the scores compare. Prompt:

> Here is the fact sheet for a document, and its humanize context. Write 12 to 15 questions a reader should be able to answer after one read of a good version of this document: the problem, each decision and the reason given for it, the asks with their owners, key numbers, the guarantees, and the open questions. Mark the 4 or 5 questions an executive must be able to answer from the title and TL;DR alone (what is wrong, what is proposed, what is guaranteed, what is asked) with `"tldr": true`. Use only `F<n>` lines; ignore lines starting with `cut ` or `assumed `. Each answer is one short sentence. Return only JSON: `{"questions": [{"id": 1, "q": "...", "answer": "...", "facts": ["F7"], "tldr": false}]}`.

## Fact audit (per version)

> Here is a document and its fact sheet (`F<n> | fact | literals | source`; ignore lines starting with `cut ` or `assumed `, and do not count their absence as a change). (1) For every fact, say whether the document still conveys its meaning: `kept`, `changed` (a qualifier, ordering, reason or decision differs) or `missing`. (2) Go through every claim in the body, captions and TL;DR: count them, and list each claim the fact sheet does not support. A claim is supported when a fact states it or it follows directly from facts; definitions of terms count as supported. Return only JSON: `{"meaning": [{"id": "F7", "status": "kept", "note": ""}], "claims_total": 0, "unsupported_claims": [{"claim": "...", "why": "..."}]}`. List every fact in `meaning`; keep notes to a few words, and empty when kept.

## Cold reads (per version)

Two agents, each told not to use any tools, which is how the prompt stands in for having none. One gets the whole doc, the other only the title and TL;DR. Each gets the quiz questions after the text, without answers.

> Read the document below once. Do not use any tools, search, or outside knowledge of these systems: answer only from the text. Then answer each question in one short sentence, or write "not stated" when the text does not say. Finally, list every term or label the text uses that you could not work out from the text itself. Return only JSON: `{"answers": [{"id": 1, "answer": "..."}], "unknown_terms": ["..."]}`.

## Grading (per version)

> Here are quiz questions with their answer keys, and two sets of answers: `full`, from a reader of the whole document, and `tldr`, from a reader of the title and TL;DR, who should only be marked on questions with `"tldr": true`. Mark an answer correct when it gives the key's substance; wording does not matter, a missing qualifier that changes the meaning does. Return only JSON: `{"full": [{"id": 1, "correct": true}], "tldr": [{"id": 3, "correct": false}], "unknown_terms": [...]}`, copying `unknown_terms` from the full-doc reader.

## Author rewrite share

After delivering a version, the next time the doc is fetched, before any new pass, diff the two: `metrics.py --author-pair delivered.md:edited.md`. It counts the share of the delivered doc's words the author changed or removed, tables and TL;DR included. Keep each delivered readback (`liveN.md`) so the pairs exist. Feedback given in chat instead of in the doc does not show up here; tally those flags in the report.
