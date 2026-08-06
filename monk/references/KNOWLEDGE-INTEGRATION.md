# monk: knowledge integration

Two halves, one file. **Priors in** is Phase 0: which of dexter's knowledge stores monk reads, how
much of each, when an entry may be cited, and what the report prints when nothing applies.
**Knowledge out** is Phase 3.5 and Phase 4e: the understand-only contract monk imposes on
`/dexter:solve`, how the verdict maps back onto a finding, and how a confirmed finding is written
into `knowledge/<slug>.md` or `LESSONS.md` so a later Phase 0 can find it.

This file is the normative owner of the Phase 0 loading budget, the applicability matching rule,
the citation format, the honest null result, the dexter invocation contract and its verdict
mapping, the knowledge router, the frontmatter / environment / body-section mappings, what counts
as a `## Data points` quantity, the `## Verification` vocabulary **and both of its `confidence`
values**, the write mechanics, and the paraphrase rule. `SKILL.md`'s `### No confidence decimal
[B-D1]` names the KB `confidence` field as the single exception to monk's no-decimal rule and
points here for the two numbers rather than repeating them; they appear nowhere else in the skill.

Cited here, owned elsewhere. Nothing below restates any of these:

- The C2 tier names **Observed** and **Asked**, and the rule that non-interactive modes defer the
  Asked tier without suspending KB writes: `SKILL.md`'s `### KB writes in non-interactive modes
  [C-D7]` is the single normative statement of that rule. A second normative copy here would
  produce exactly the broader-prohibition misreading that section warns against.
- **Emission-bar raising**, the three concrete changes that fire when `declined` exceeds
  `confirmed` over the outcome window: `SKILL.md`'s Phase 0 `### Prior state`.
- The **calibration-window retrieval** (the glob over `reviews/`, the sort key, the frontmatter
  `counts:` header read): `references/PERSISTENCE.md`.
- The ledger fields this file branches on, `pending_kb`, `pending_ask`,
  `proof: {dexter_case, fact, fact_anchor}`, and the four `status` values `carried`, `addressed`,
  `declined`, `unobservable`: `references/PERSISTENCE.md`.
- The killer token `dexter-refutation` and the rest of the closed killer vocabulary:
  `references/METHOD.md`.
- Tier names, the tier lookup, the reporting floor, and the caps: `SKILL.md`.
- The `## Priors` report block that renders this file's citation format:
  `references/REPORT-TEMPLATE.md`.

---

# Part 1: priors in (Phase 0)

## What is loaded

| Source | How much | Why |
|---|---|---|
| `~/workspace/investigations/KNOWLEDGE.md` | whole file (3.2KB, ~800 tokens) | Index lines already carry domain, environment, and tags: exactly the three filter fields [F-D9] |
| `~/workspace/investigations/LESSONS.md` | `## ` headings only (~400 tokens), then open 0 to 3 bodies whose heading is relevant | The file is 20.9KB across 23 entries with no tags, domain, or index, so the environment/domain/tags filter cannot apply to it at all. Injecting 5 to 6k tokens of GPU-perf lore into a Thrift or Hack review is both cost and a manufacturing hazard: it primes perf-flavoured Human Judgment items [F-D9] |
| `knowledge/<slug>.md` | at most 3 full entries, ranked off KNOWLEDGE.md index lines alone [F-D6] | `kb.py search` counts raw substrings over the whole body with a 5x head weight, so `search error` scores 35 on an unrelated CUDA entry. Score > 0 is not applicability |
| `~/workspace/investigations/reviews/D<n>.md` if present | whole file | Carried findings, declined suppressions, and the outcome window [C-D10][F-D5] |

Phase 0 lookup of **this diff's** prior state is a single file-exists check on the diff number. No
index file is needed [C-D1].

The **calibration window** is a second, cheap read over the other ledgers, whose retrieval
`references/PERSISTENCE.md` owns: glob the ledger directory, sort by the frontmatter `last_review`
field descending, and read only the frontmatter `counts:` map of each until roughly 20 emitted
findings are accumulated. `counts:` is in frontmatter precisely so this is a header read, not a
full parse, and so it still needs no index file.

## Applicability matching rule [F-D6]

Both conditions are required:

1. **Identifier overlap.** A concrete identifier drawn from the entry's tags, title, or root cause literally appears in the diff or in a file monk read for it: a symbol, config key, API, flag, or path component. Topic words ("config", "error", "test") do not count.
2. **Environment not contradicted.** The entry's `environment.surface` and `environment.stack` must be compatible with the diff's. A MAST-training entry never applies to a www/Hack diff.

Applicability is decided by the code, never by the directory the diff lives in.

## Citation format [F-D7]

A prior may be cited only if monk can write this falsifiable sentence:

```
[[slug]] proved mechanism M under condition C; this diff creates C at <file> :: <symbol> (line L).
```

If that sentence cannot be written, the entry is background context and must not appear as a
citation. Format is `[[slug]] §Section`, matching the existing `[[hf-sft-fsdp-lever-sweep]]`
convention in LESSONS.md.

- A prior never raises severity by itself.
- A finding resting only on a prior whose frontmatter `status` is not `confirmed` cannot be Must Fix.
- **Correction to the source spec.** "Guardrail absent from the diff's area = a finding with a citation" is withdrawn. All 7 current entries' `Prevention` text is investigator triage advice ("check dataloader worker lifecycle before blaming GPU/comms", "confirm which stack the config runs on"), addressed to an investigator, not a reviewer. Taken literally the old rule fires on every diff that merely touches the topic. `Prevention` and `Generalizable lesson` now yield a **Decisions to Validate** item at most, unless the predicate sentence above passes, in which case the normal chain rules apply.

## The honest null result [F-D8]

`Priors:` is a mandatory printed field in every report, never omitted:

```
Priors: 7 scanned, 0 applicable (KB is gpu-training-perf / cuda-kernel-debugging; this diff is <surface>/<stack>)
Priors: 7 scanned, 1 applicable
  [[dataloader-persistent-workers-epoch-respawn]] §Prevention - matched identifier `persistent_workers` at trainer/config.py:88
```

Because absence must be stated and the reason named, there is no silent gap for a stretched
citation to fill. C6 concedes that all 7 entries are `gpu-training-perf` or
`cuda-kernel-debugging` and that most diffs will legitimately have no applicable prior.

---

# Part 2: knowledge out (Phase 3.5 and Phase 4e)

## The invocation contract (safety-critical) [A-D7]

`/dexter:solve` normally drives through to a verified fix and mandatorily banks a knowledge entry
at its step 8. Left unqualified, a monk escalation would fix the diff under review and bank
unconfirmed entries, violating Phabricator-read-only and C2. monk therefore invokes it
**understand-only**:

| Clause | Value |
|---|---|
| Goal | `decide proposition P` |
| Definition of done | a verdict on P, nothing more |
| Fix / repair phase | **suppressed.** monk reports, never repairs |
| `knowledge/` write | **suppressed at invocation, unconditionally.** Not "suppressed on a kill": at escalation time the finding is not yet C2-confirmed, so dexter banking anything at all would violate C2. A refuted proposition yields at most a `LESSONS.md` line and never a `knowledge/<slug>.md` entry. **Consequence: dexter never banks an entry for a monk escalation, so monk always authors it itself** (see the ownership rule in the KB section) |
| Working copy | **must not modify tracked files.** Under C1 uncommitted mode the dirty working copy IS the artifact under review |
| Scope | read-only, local, single-host probes by default; see the consent rule below |

All six clauses are passed on every invocation. Dropping any one of them turns a read-only
reviewer into a process that edits a diff the user may not own.

**The consent rule.** Local, read-only, single-host probes run without asking. Anything that needs
a remote job (MAST, GPU), and any escalation at all on a diff the user did not author, is printed
first as a list of propositions plus estimated cost and asked once, batched, never per escalation.
Never launch a job against another author's config without saying so.

A proven proposition that establishes a real defect is C2's "dexter proved it". Because the write
was suppressed here, **monk itself authors that entry**, once the finding is confirmed, per the
ownership rule in the KB section.

## Escalation volume in repo mode

`SKILL.md`'s Phase 3.5 puts expected volume at 0 to 2 escalations per diff. Repo mode multiplies
that expectation by the unit count: a 25-unit run is 25 chances to reach the same expectation, and
the obvious response is a per-run escalation budget. There is **no per-run budget**, and adding one
would be wrong on two counts.

- It contradicts the unlimited escalation budget C3 grants for facts reading cannot settle. That
  phrase is already narrow, because `SKILL.md`'s three-way unknown split sends readable unknowns
  back to reading and kills unfalsifiable ones outright, so the only thing a per-run cap could
  actually ration is the empirical set, which is exactly the set the budget exists to pay for.
- It parks an unsettled factual unknown. A run that has spent its budget can only report the
  finding as "a chain that would have escalated but could not", which is a factual unknown resting
  in a tier. Goal 5, prove or kill, says a factual unknown is settled by reading, by dexter, or by
  dropping the finding, and gate 1 of `SKILL.md`'s Human Judgment gates says factual uncertainty
  may not rest there. A per-run cap would be a third disposal route that both of them forbid.

What bounds the volume instead is the eligibility rule that already exists: only an **otherwise
complete** chain may escalate, meaning every non-empirical link is proven and the terminal is
named. Most unknowns never reach that point. They die earlier at reading, at weakening into a
proven weaker link, or at trigger satisfiability. A unit that produces no complete chain produces
no escalation, and the per-unit expectation of 0 to 2 is dominated by the 0.

If real runs show otherwise, the honest response is calibration, not a rule invented ahead of the
measurement: record escalations per unit across roughly 20 unit reviews, and if the count is
routinely at the top of the band rather than the bottom, the thing that is too loose is the
eligibility rule or the unknown split, not the budget.

## Verdict mapping

| Dexter verdict | Effect on the finding |
|---|---|
| `proved` | The link becomes READ-equivalent with the dexter case cited as proof. Finding proceeds to tiering, Must Fix eligible |
| `refuted` | Finding is **dropped**, not demoted [C3]. Logged in `Chains abandoned` tagged `killer: dexter-refutation`. Optional `LESSONS.md` line |
| `blocked` | Human Judgment, **with the blocker named** [A-D7] |
| did not terminate ("inconclusive") | Human Judgment marked `escalated, unsettled`, citing dexter's partial evidence and the concrete blocker (needs a 32-GPU repro; path only reachable in a prod config nobody can run) [B-D8] |

"Inconclusive" is not a verdict, so C3's prove-or-kill is untouched: the escalation simply did not
terminate. Budget is not omniscience. This is the **sole** route by which a finding with an
INFERRED link may appear in Human Judgment, and it must display the blocker so the reader knows
what was tried.

A dexter refutation still teaches something, and it goes to `LESSONS.md`: "this chain class looks
fatal but X makes it safe, check X first" is exactly the process learning that stops the next
review burning an escalation on the same dead end. It never touches `knowledge/`. C3 governs the
report, not memory.

## The router [D-D1]

Both stores exist, and the KB schema itself is the router. A **confirmed** finding (C2) earns
`knowledge/<slug>.md` only if it can honestly fill all seven sections: a durable artifact (the
author's fix hunk, or a dexter case) plus at least one real quantity for `## Data points`.

| Finding | Destination |
|---|---|
| Confirmed, has a durable artifact and a real quantity | `knowledge/<slug>.md` |
| Confirmed, contract-only defect or no measurable scope | `LESSONS.md`, with a `[[slug]]` backlink where one exists |
| Review-process learning ("this class hides at this seam", "this reviewer prompt suppresses this class") | `LESSONS.md`, always, regardless |
| Refuted by dexter | `LESSONS.md` at most; never `knowledge/` |
| Unconfirmed, including everything low-confidence monk deliberately publishes | neither |

No third store.

## Ownership when a finding was escalated [D-D7]

`/dexter:solve` step 8 mandatorily banks a knowledge entry plus `kb.py index`. monk's invocation
contract (Phase 3.5 step 4) suppresses that write **unconditionally**, because at escalation time
the finding is not yet C2-confirmed and a refuted proposition must bank nothing. **Consequence:
dexter never banks an entry for a monk escalation, and monk always authors the entry itself**,
after C2 confirmation.

The one-slug rule still binds, on a different path. Write mechanics step 1 runs
`kb.py search <mechanism terms>` before writing, and that can surface a pre-existing entry for the
same mechanism from an earlier **standalone** dexter investigation, one monk did not commission.
In that case monk edits in place and never creates a second slug: two near-identical slugs would
poison the domain and tag lookup Phase 0 depends on.

| Case | Owner |
|---|---|
| Escalated, dexter proved it | **monk authors the entry** after C2 confirmation, with `## Verification` = `proved-by-experiment` citing the dexter case dir. Dexter banked nothing, because the write was suppressed |
| Escalated, dexter refuted it | no entry, ever. `LESSONS.md` at most |
| Escalated, `blocked` or unsettled | no entry. The finding sits in Human Judgment and is not confirmed |
| Never escalated, confirmed via C2 | monk authors the entry |
| `kb.py search` surfaces a pre-existing entry for the same mechanism (an earlier standalone dexter case, or a monk entry from another diff) | monk **edits it in place**: append the diff to `source_refs`, add the review-time chain to `## Root cause`, fill `## Fix` and `## Prevention` once the author's change lands, then re-validate and re-index. Never a second slug |

## Frontmatter mapping [D-D2]

`kb.py` requires exactly these 12 keys, all non-empty:
`id, title, date, goal, outcome, source, source_refs, environment, domain, tags, confidence, status`.

| Field | Value for a review finding |
|---|---|
| `id` | the **mechanism** slug (`narrow-except-strands-ranks`), never `d114284934-finding-2`. Provenance belongs in `source_refs` |
| `title` | mechanism to consequence, one sentence |
| `date` | date of **confirmation**, not of review |
| `goal` | the proposition the review had to settle, plus its definition-of-done |
| `outcome` | `goal-met` when fixed; `handed-off` when confirmed but unfixed |
| `source` | `own_investigation` (the validator does not enforce the enum, but consumers assume it) |
| `source_refs` | diff ID, the two versions compared, and the dexter case dir if escalated. For a finding first raised in C1 uncommitted mode, the fallback ladder in the input-resolution section: `D<number>` if one now exists, else the dexter case dir, else the base commit hash captured at review time plus the changed paths. Minimum 1, and every ref must still resolve later |
| `domain` | the defect's **technical area**, never `code-review`, or Phase 0's domain-overlap lookup never fires |
| `tags` | the mechanism's terms, plus `caught-in-review` and `monk` |
| `confidence` | 0.95 for proved-by-experiment; 0.9 for proved-by-reading plus corroborating fix. Never below, since only confirmed findings arrive here |
| `status` | always `confirmed`. monk never writes `provisional` [B-D10] |

`KNOWLEDGE.md` and `kb.py search` key on title, domain, and tags at 5x weight, so a
provenance-shaped slug or a `code-review` domain would make monk's entries invisible to the exact
Phase 0 lookup they exist to feed.

Do not add a distinguishing key such as `evidence: predicted-not-observed`. Nothing reads unknown
keys, while tags sit in `kb.py search`'s haystack at 5x weight. The `caught-in-review` tag plus the
"Predicted" first line of `## Symptom` already carry it.

## The five-field environment block [D-D3]

`kb.py` requires `org, surface, hardware, workload, stack`. Describe **where the defect would
fire**, not where the review happened, since lookups filter on it.

| Key | Source |
|---|---|
| `org` | `Meta` |
| `surface` | the diff's own config and test plan (`MAST`) |
| `workload` | what the change runs (`DCP to HF checkpoint conversion`) |
| `stack` | `python/PyTorch FSDP, fbcode/mitra` |
| `hardware` | the target topology the diff names (`8xH100, world_size 8`). Use `N/A` only when the defect is genuinely hardware-independent |

The review surface (fbsource, Phabricator) goes in `source_refs` and `## Verification`, never in
`environment`.

`validate()` permits the literal `N/A` only when the string `hardware` appears within the 40
characters preceding it. Anywhere else in the file it fails the entry.

## The seven body sections

`kb.py` requires `Symptom, Root cause, Fix, Prevention, Data points, Generalizable lesson,
Verification`, each at least 25 characters, and `Data points` must contain at least one digit.

| Section | Rule for a review finding |
|---|---|
| `## Symptom` [D-D4] | Write what a future searcher would paste, in runtime vocabulary, explicitly marked predicted. Line 1: `Predicted, never ran in production; caught reviewing D<n> v<k>.` Then the concrete failure (which ranks or requests block, on what call, what kills them). Then `Review-time evidence:` with `file:line` facts. **Never invent an error string**: quote one only if cited from library source or reproduced by dexter; otherwise describe the failure without quoting |
| `## Root cause` | the chain, link by link, with each link's citation and grade |
| `## Fix` [D-D8] | what the author actually changed, cited by version and hunk. When confirmed but never fixed (diff abandoned, or landed as-is), state that plainly plus the recommended fix; it is honest, exceeds the 25-char stub check, and validates |
| `## Prevention` [D-D8] | monk's highest-value field, because Phase 0 reads `Prevention` as a lens. Name the lint rule, assertion, type change, or test that would have caught this, or state that no guardrail exists and name the gap. Pre-merge, it will usually be the gap |
| `## Data points` [D-D5] | see below |
| `## Generalizable lesson` | the transferable heuristic, written for a reviewer, not for an investigator |
| `## Verification` [D-D6] | see the fixed vocabulary below |

## `## Data points` for a bug that never ran [D-D5]

| Legitimate | Illegitimate |
|---|---|
| blast radius (7 of 8 ranks) | diff and version numbers |
| magnitudes read from code or config (35B gather, 1800s watchdog default) | dates |
| coverage counts (the `except` covers 1 of 6 raisable exception types) | confidence scores |
| anything dexter measured | finding counts |

Open the section with `Derived from code/config at review time, not measured:` and list any
dexter-measured numbers separately under `Measured:`. `validate()` only greps for any digit, so
the bar has to be editorial; identifiers are provenance, not properties of the failure, and
admitting them would let every finding game the gate. **If no quantity of the failure exists, the
finding is LESSONS-only.**

## `## Verification` vocabulary [D-D6]

Name the strongest thing that actually happened. An entry must never claim a stronger kind than it
holds.

| Label | Content | `confidence` |
|---|---|---|
| `proved-by-experiment` | dexter case ref plus what was measured | 0.95 |
| `proved-by-reading` | each chain link cited `file:line` at a named revision, plus what would have falsified the chain and why that does not hold | 0.9 with corroboration |
| `corroborated-by-fix` | the author's hunk and version, plus any test they added | contributes to 0.9, never alone |

An author fix is corroboration, not proof; authors also fix to unblock review.

## Write mechanics [D-D10]

1. `python3 ~/workspace/plugins/dexter/scripts/kb.py search <mechanism terms>`. If an entry for the same mechanism exists, **update it** (extra `source_ref`, extra data point, bumped date) rather than creating a near-duplicate slug.
2. Write the entry.
3. `python3 ~/workspace/plugins/dexter/scripts/kb.py validate <path>` until clean.
4. `python3 ~/workspace/plugins/dexter/scripts/kb.py index` to regenerate `KNOWLEDGE.md`.
5. Commit in the investigations repo as `knowledge: <slug> ...` or `lesson: ...` per its `CLAUDE.md`.

`kb.py` exposes exactly four commands (`validate`, `search`, `index`, `template`) and does not
support `--help` [C5].

## The placeholder landmine and the paraphrase rule [D-D10]

`validate()` lowercases the **entire file** and rejects it if any of five placeholder substrings
appears **anywhere**, as a bare substring with no word boundary. Spelled with separating hyphens
here for exactly the reason the rule exists, the five are `t-o-d-o`, `f-i-x-m-e`, `x-x-x`,
`t-b-d`, and a run of three question marks. Code-review entries quote source code, so a quoted
deferred-work marker comment or a danger marker silently fails validation. So does an innocent
substring buried in an unrelated identifier: a hex literal whose digits happen to spell the
three-character danger marker, or a symbol name carrying the to-be-determined abbreviation between
underscores. Word boundaries do not save the entry, because the check is a bare substring scan.

**Paraphrase rule.** Never paste a source line containing any of those substrings. Instead:

- Cite the line by `file:line` and describe it: "a deferred-work marker comment at `convert.py:88` says the dtype path is unfinished."
- Never reproduce the marker token itself, in any case, even inside a fenced code block.
- Elide the offending token from an otherwise-necessary quote and mark the elision.
- Run `kb.py validate` before commit; a placeholder failure means find the quoted line and paraphrase it.

The same applies to `N/A` outside the `environment.hardware` window.

This file obeys its own rule. The five substrings are spelled hyphen-separated above so that the
one file in the skill that teaches the paraphrase rule would itself survive the validator it
describes.

When an `addressed` finding cannot be written as a valid entry, do not write a degraded one; the
schema's position is that holes are worse than nothing. Park it as `pending_kb: true` in the
reviews file, report which fields are missing, and let the user supply them or route the finding to
`LESSONS.md` instead.

## Verbal corroboration with no artifact goes to `LESSONS.md`, and there is no `provisional` hatch

A finding the user corroborates verbally but that has **no fix hunk and no dexter case** goes to
`LESSONS.md` only. **`status: provisional` is deleted as an option**, not relaxed: B-D10, the
frontmatter mapping table, and Out of Scope all state that monk writes `status: confirmed` entries
exclusively, and a fourth site permitting `provisional` would leave the rule two-valued and
unimplementable.

Deleting the hatch costs nothing, because such a finding already fails the D-D1 router on its own
terms and would have to be forced past three other gates to reach `knowledge/` at all:

- `## Verification` has a fixed three-label vocabulary [D-D6]. A verbal "yes, that looks right" is none of `proved-by-experiment`, `proved-by-reading`, or `corroborated-by-fix`, and D-D6 forbids claiming a stronger kind than the entry holds.
- `## Data points` needs a real quantity of the failure [D-D5], and D-D5 already ends "if no quantity of the failure exists, the finding is LESSONS-only".
- `confidence` is a fixed lookup off the `## Verification` label [B-D1], so there is no label that yields 0.7 and no judgment step that could produce one.

If the user insists on a KB entry, the answer is to **produce the missing artifact** (land the fix,
so `corroborated-by-fix` applies, or run the dexter case, so `proved-by-experiment` does), never to
weaken the status field. A `LESSONS.md` entry naming the human and the date carries the same
knowledge at the honest strength, and Phase 0 reads `LESSONS.md` headings on every run anyway.

## `LESSONS.md` authoring [F-D10][C5]

- Format is **Lesson / Why / How to apply**, newest at the top.
- Heading carries a review marker: `## <date> [review] <one-line lesson>`, so Phase 0's heading-only scan can filter by audience.
- **At most one review-craft lesson per review**, and only after scanning existing headings to confirm no entry covers it. Never per-review boilerplate.
- Write a lesson only when it changes future reading.
- When headings exceed ~60, move the oldest to `LESSONS-ARCHIVE.md`, which is never auto-loaded and is searched only on demand.

At ~130 words per lesson, one per review adds ~1KB per run; 100 reviews would push an
always-loaded file past 25k tokens, which is why Phase 0 loads headings only.

Review-craft lessons share `LESSONS.md` with dexter's investigation lessons rather than living in a
separate file. Cross-pollination is real, and one loop is simpler; the `[review]` heading marker is
what lets Phase 0's heading-only scan filter by audience.

## Open calibration questions

This value is binding today. It names what would change it.

- **`LESSONS.md` growth** is bounded by three rules already in force: the `[review]` heading marker, at most one review-craft lesson per review and only when it changes future reading, and archiving the oldest headings to `LESSONS-ARCHIVE.md` past roughly 60. The file is 21KB today and Phase 0 reads its headings on every review. If it passes roughly 40KB, consider splitting by domain.
