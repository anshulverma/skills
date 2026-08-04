---
name: monk
description: Use when reviewing a Phabricator diff, a diff stack, or an uncommitted working copy for real defects - deadlocks, hangs, silent wrong numerics, unbounded resource growth, ACL or PII leaks, wrong persisted artifacts - particularly when the failure needs a multi-step causal argument across several files rather than a single suspicious line. Also use when re-reviewing a later version of a diff monk already reviewed, or when deciding whether a previously flagged concern was addressed. Not for style, naming, formatting, or anything a linter owns.
---

# monk

monk reviews a diff by constructing whole causal chains from the changed lines to an observable
terminal failure, grading every link against a citation, and delivering the survivors to the user.
It never touches Phabricator: no comment, no inline note, no signal, no accept or reject, no diff
update.

What produces the delta over existing reviewers is aperture and whole-chain custody. It is **not
fan-out**, **not adversarial verification**, **not model class**, and **not team invariant rules**;
`references/ANTI-PATTERNS.md` carries those four load-bearing negatives with the evidence against
each, quoted from the competing reviewers' own prompts.

## Goals

1. **Whole-chain review** - hold each causal chain end to end in one reasoner, never split by lens.
2. **Auditable warrant** - every link carries a grade and a citation, so "proven" is a checkable property rather than a tone.
3. **Honest emptiness** - "nothing found" is the expected outcome and is a first-class, evidence-bearing report.
4. **Bounded speculation** - trigger conditions are derived mechanically and tested for satisfiability in the repo; unsatisfiable chains die.
5. **Prove or kill** - a factual unknown is settled by reading, by dexter, or by dropping the finding; it never rests in a tier.
6. **Phabricator-read-only** - monk never posts a comment, signal, or diff update, and writes only under `~/workspace/investigations/`.
7. **A closed feedback loop** - findings persist per diff, outcomes are observed across versions, confirmed findings graduate to the knowledge base, and review craft graduates to `LESSONS.md`.

## Non-goals

- Style, naming, formatting, convention. Lint owns these. Restating a style objection as a "maintainability risk" or "readability concern" is the same objection and is equally out of scope [F-D4].
- Replacing human review. On D114284934 the human made two findings no bot made, including the architectural one.
- Approving, rejecting, landing, or updating anything in Phabricator.
- Reviewing bot-authored or codemod diffs by default. `--include-bots` is the override; see the flag table in Input resolution.
- Producing a confidence decimal in report output. monk never prints or is asked for one [B-D1]. The KB's schema-mandated `confidence` frontmatter field is the sole exception and is a fixed lookup off the `## Verification` label, not a review judgment.

## Definition of done

The report distinguishes what is provably broken from what warrants a human's judgment, anchors
every item at a file plus enclosing symbol, states a derived and satisfiable triggering
condition, names what work was done (priors scanned, files read, chains abandoned, coverage), and
says "nothing found" cleanly when that is the truth. Silence produced by a crashed agent or a
skipped file is not a finding of nothing [E-D9].

## Evidence base and calibration

The census is a census, not a sample: 929 diffs, 18 real critical catches, 16 unique (~1.7%).
Six of the 18 came from a Skycastle invariant audit on a single lint-replicable rule. Of the 12
LLM catches, 3 are pyre/buck territory, 2 dedupe, and 3 were independently flagged by another AI
reviewer. Residual novel logic catches: roughly 4 to 5 across 929 diffs. Thirteen strict Must-Fix
summaries, one refuted by a human (7.7% red-tier false positive rate); no false-positive rate was
ever measured on the lower tiers that dominate output.

**Consequence: most reviews find nothing. A skill that always emits a Must Fix is broken.**

### How that is enforced in skill text, not merely asserted

The 1.7% line ships in `SKILL.md` and in every per-file agent brief, but it does no enforcement
work by itself. Enforcement is structural [F-D1]:

| Mechanism | Rule | Where |
|---|---|---|
| No legal resting place for a hunch | Human Judgment is redefined as *judgment* items only: trade-offs a human must settle with product or author context. Uncertainty about a fact may not rest there. | Tier rubric |
| Fact-uncertainty must exit | Any factual unknown is read, escalated per C3, or kills the link. Escalation returns Must Fix (proof cited) or dropped. It never demotes into a tier. | Phase 3.5 |
| Killed chains get a destination | Every abandoned chain is logged with its terminating reason in the required `Chains abandoned` field. The urge to report has a home that costs the author nothing. | Report |
| A clean report is long, not empty | The clean report is where monk demonstrates work: priors scanned, files read and why, chains pushed and abandoned. Removes the incentive to demonstrate work via a finding [F-D2]. | `REPORT-TEMPLATE.md` |
| Structural floor | Three drop rules, no numbers, plus an explicit prohibition: never emit a finding so the report is not empty [B-D4]. | Tier rubric |
| Volume caps | Human Judgment capped at 3 by displacement, Decisions to Validate capped at 3 by displacement. Agents have no quota and are graded on chain completeness and open-end honesty, never on finding count [B-D5][E-D8]. | Orchestrator |
| Measured, not asserted | The per-diff ledger records each finding's outcome. Phase 0 reads the last ~20 outcomes and the report header prints them. If declined exceeds confirmed over the window, raise the emission bar this run, which is three specific rule changes defined in Phase 0, not a mood [F-D5]. | Phase 0 + report |

## Architecture

```
/monk [D<n> | --stack] [--gchat] [--include-bots]
  |
  v
Phase 0  Priors + prior state
         KNOWLEDGE.md (full) + LESSONS.md (headings) + reviews/D<n>.md
         -> applicable priors, carried findings, declined suppressions, outcome window
  |
Phase 1  Intent           author's claim, recorded before any code is read
  |
Phase 2  Read             full files both versions + dependencies a link needs
  |
Phase 3  Chain            root -> graded links -> first terminal; trigger derived; negation-tested
         |
         +-- <=5 reviewable files: one reasoner
         +-- >5: stage 1 per-file agents -> open-end ledger -> stage 2 completion agents
  |
Phase 3.5 Escalate        3-way unknown split -> weaken -> orchestrator dedupes by
                          proposition -> concurrent understand-only /dexter:solve
  |
Phase 4a Tier             deterministic lookup over READ/INFERRED/ASSUMED + floor + caps
Phase 4b Persist          classify vs previous version, write reviews/D<n>.md (single writer)
Phase 4c Ask              one batched prompt for unobservable findings (interactive only)
Phase 4d Report           terminal, or --gchat
Phase 4e Bank             confirmed -> knowledge/<slug>.md; craft -> LESSONS.md
```

Markdown only, no scripts, no plugin. Lives at `~/workspace/skills/monk/` and symlinks into
`~/.claude/skills/monk`.

```
~/workspace/skills/monk/
  SKILL.md                        # phases 0-4, tier lookup, floor, caps, calibration, verdict map
  references/
    METHOD.md                     # seven rules, warrant grades, terminal classes, trigger derivation
    ANTI-PATTERNS.md              # what other reviewers do wrong, quoted from their prompts
    REPORT-TEMPLATE.md            # exact output structure + both verbatim worked examples
    FANOUT.md                     # brief template, open-end ledger, stitch, dedup, coverage
    PERSISTENCE.md                # reviews/D<n>.md schema, matching, ask protocol, suppression
    KNOWLEDGE-INTEGRATION.md      # prior selection/citation, dexter contract, KB + LESSONS authoring
```

### The seven rules

1. Never fan out by lens.
2. Fan out by file or subsystem only.
3. Read whole files, both versions, including untouched dependencies.
4. Runtime and system state are in scope.
5. Never drop the 0.5 to 0.8 band; demote it.
6. A code comment is a hypothesis, not an alibi.
7. Diff the code against the author's own summary.

Rationale and evidence: `references/METHOD.md`.

## Input resolution (C1)

| Invocation | Resolves to | Persistence |
|---|---|---|
| `/monk D114284934` | that diff | `reviews/D114284934.md` |
| `/monk` | current commit's diff, via `sl log -r . -T '{phabdiff}'` | `reviews/D<n>.md` |
| `/monk` with no diff on the commit | uncommitted working-copy changes, via `sl diff` | none [C-D9] |
| `/monk --stack` | every diff base-to-top, each reviewed separately | one file per diff |

Pre-publish review is in scope: catching a deadlock before publication is the cheapest place to
catch it. With no Phabricator summary, the intent check falls back to the commit message; with no
usable statement of intent, the report says so rather than inventing one.

Uncommitted mode has no stable identity, is overwritten continuously, and has no later version to
compare against, so no ledger is written and findings are reported and discarded [C-D9]. Stated
consequence for `SKILL.md`: **a pre-publish finding can reach the KB only through the Asked tier
of C2, never through the Observed tier.** When the change becomes a `D<number>`, monk starts a
fresh ledger file.

**Durable `source_refs` for an uncommitted-mode finding.** `kb.py` requires at least one
`source_refs` entry, and a KB entry that outlives its own provenance is worthless, so an
Asked-tier confirmation raised in uncommitted mode uses, in this order of preference: the
`D<number>` if one exists by the time the confirmation is given; the dexter case dir if the
finding was escalated; otherwise the base commit hash the working copy sat on at review time
(`sl log -r . -T '{node}'`, captured in Phase 0 and printed in the report header) plus the changed
paths. Never a bare date and never a working-copy path, neither of which resolves later.

### Flags

`--gchat`, `--stack`, and `--include-bots` are independent and may be combined freely. No flag
changes what monk reasons about; each changes only delivery, iteration, or admission.

| Flag | Effect |
|---|---|
| `--gchat` | Deliver the report through `meta google.chat.message send` instead of the terminal. A delivery channel only; its one behavioral consequence, the deferred Asked tier, is stated in Delivery |
| `--stack` | Review every diff base-to-top, each against its own base, one ledger file per diff |
| `--include-bots` | Review a bot-authored or codemod diff, which is skipped by default |

**`--include-bots` is the override the non-goal implies.** Bot and codemod diffs are skipped by
default because a codemod's causal chains are properties of the codemod, not of the diff, so the
same finding would be re-derived on every one of its N output diffs. With the flag, monk reviews
the diff under the ordinary rules with no special casing. Without it, monk prints one line naming
the detected bot account or codemod tag, writes no ledger file, and exits, so a skip is never
mistaken for a clean review and never contributes a `Clean` verdict to the calibration window.
Detection is by the diff's author being a known bot account or its summary carrying a codemod tag;
**when detection is uncertain, review the diff**, because a wasted review is cheaper than a silent
skip, exactly as with the `@generated` sniff in the fan-out section.

**`--stack` with `--gchat`: one message per diff.** Each diff's report is sent as its own message
the moment that diff's review completes, with a `[k/N] D<number>` prefix on the first line. A
single combined message is rejected: the reports have independent verdicts and independent
`Calibration` blocks, and concatenating them buries a `Needs Fixes` inside a wall of `Clean`.
One final one-line summary message follows the last diff, listing each diff and its verdict.

## Phase 0: priors and prior state

### What is loaded

`references/KNOWLEDGE-INTEGRATION.md` owns the loading budget table (which of `KNOWLEDGE.md`,
`LESSONS.md`, and `knowledge/<slug>.md` is read, how much of each, and why), the applicability
matching rule, the citation format, and the honest null result. Load exactly what that table
allows and no more: over-injecting unrelated lore is not a cost problem, it is a manufacturing
hazard that primes findings in the flavour of whatever was injected.

Phase 0 lookup of **this diff's** prior state is a single file-exists check on the diff number. No
index file is needed [C-D1].

The **calibration window** is a second, cheap read over the other ledgers. `references/PERSISTENCE.md`
owns its retrieval: the glob over `~/workspace/investigations/reviews/`, the sort key, and the
frontmatter `counts:` map that makes it a header read rather than a full parse.

### Prior state

- Load carried findings from the previous version and seed them as already-known [C-D10].
- Apply `declined` suppressions: match new candidate findings against declined anchor plus predicate and do not re-raise them [C-D8].
- Read the last ~20 recorded outcomes across ledger files for the calibration header [F-D5], by the glob-and-sort retrieval above.

**Raising the emission bar** (when `declined` exceeds `confirmed` over that window) is three
concrete changes for the current run, not a mood:

1. The Human Judgment cap drops from 3 to 1.
2. A Must Fix requires its trigger to be satisfied by a config, test, or call site monk actually read. An argued-satisfiable trigger is no longer sufficient and demotes the finding.
3. Any chain still carrying an **escalated-unsettled** link is dropped rather than published as conditional. A residual ASSUMED link is NOT dropped: it is the ordinary Human Judgment case, and dropping it too would empty the tier entirely and make rule 1's tightened cap unreachable.

The report's `Calibration` block states that the bar was raised and prints the window that
triggered it.

## Phase 1: intent

Extract the claimed goal from title, summary, and test plan, and record it verbatim **before**
reading code, so the code is read against the claim rather than the claim being rationalized from
the code. Under C1 uncommitted mode, fall back to the commit message; if there is no usable
statement of intent, print `Intent: none stated` and skip the EXTRA/MISSING comparison rather
than inventing one.

The recorded intent is passed verbatim into every per-file agent brief [E-D2 block 2], and the
diff-global EXTRA/MISSING comparison is assembled from the per-file behavioral deltas [E-D3].

```
## Intent
<the author's claim, quoted or tightly paraphrased>

## Intent vs Implementation
ALIGNED
EXTRA:   <behavior the diff adds that the summary does not claim>
MISSING: <behavior the summary claims that the diff does not implement>
```

## Phase 2: reading aperture

- Full files, both versions, not hunks.
- Plus every file a chain link actually needs: exception hierarchies, base classes, callers of changed signatures, the config or test-plan job the change targets.
- A file is opened because a link needs it, and the reason is recorded. The report's `Read` field lists changed files plus each untouched dependency opened with why it was opened [F-D2].
- Library semantics recalled from memory is not evidence. When the library source is in the repo, read it; a grade B link cites that path or a doc URL [A-D2].
- Aperture is unlimited for reading and bounded for reporting by the chain-root rule in Phase 3 [A-D9], which is what keeps full-file aperture from becoming a repo audit.

## Phase 3: chain construction

A chain is a rooted, directed sequence of graded links terminating in exactly one terminal class.

Warrant grades A through E and the evidence each demands are defined in
`references/METHOD.md#warrant-grades`. The sections around it in the same file own the rest of the
construction vocabulary: where a chain may start, edge kinds, trigger derivation and
satisfiability, the closed list of terminal classes T1 through T6 with their stop rules, the
negation test, the residual-unknown bound, the chain predicate, and the closed killer vocabulary.
Cite `references/METHOD.md` by section; never restate one of its tables here.

Fan-out triggers when the count of reviewable changed files rises above the threshold, at which
point the diff is reviewed by per-file owner agents in two stages rather than by one reasoner.
`references/FANOUT.md` owns the threshold table, what counts as a reviewable changed file, the
brief template, the open-end ledger, the stitch, dedup, and the coverage ledger. Fan-out is by
file or subsystem only, never by lens, at every level including inside an owner agent.

Owner agents run in bounded waves under a concurrency cap, whose number `references/FANOUT.md`
owns along with the change-inlining budget. The cap is recorded here because it is a source of
partial coverage: when a wave does not complete, the shortfall is a coverage-ledger entry and a
`Clean (partial: ...)` verdict, never silence [E-D9][E-D10].

### Warrant-to-annotation crosswalk

Phase 3 grades warrants; Phase 4a tiers annotations. The mapping is fixed, so the two rubrics are
one rubric:

| Warrant grade | Annotation | Consequence |
|---|---|---|
| A | READ | none |
| B, in-repo source opened this run | READ | none |
| B, doc URL or recalled semantics only | INFERRED | not tierable; enters Phase 3.5 triage |
| C, arithmetic and denominator both from values read | READ | none |
| C, no denominator | demoted to D | consumes the residual slot |
| D | ASSUMED | consumes the residual slot |
| E | not a link | chain dies |

## Phase 3.5: dexter escalation

A distinct phase between Chain and Report [B-D7]. **No finding is tiered until every escalation
returns.** Consequences to design around: the report is not streamable, nothing prints until the
last verdict lands; a single verdict can retier several findings at once because dedup is by
unproven fact; and the escalation key is the proposition, not the finding.

### Step 1: three-way unknown split [A-D5]

C3 grants an unlimited escalation budget for facts "reading cannot settle". That phrase already
excludes two categories, so classify first:

| Unknown kind | Test | Action |
|---|---|---|
| Readable | Another file in the repo settles it | Read it. Escalating a read is the waste an unlimited budget invites |
| Empirical | Needs execution, measurement, or real runtime state | This and only this is C3's escalation set |
| Unfalsifiable | Author intent; "a future caller could"; "someone might" | Kills the link. Dexter cannot settle it either |

### Step 2: weakening [A-D5]

Before escalating, ask whether the unproven link can be replaced by a weaker **proven** link
reaching the same terminal. "Any exception that is not `MitraRuntimeError`" beats "this specific
call OOMs" and needs no investigation at all. Weakening is attempted on every escalation
candidate and the attempt is recorded.

### Step 3: eligibility and concurrency [A-D6]

- Escalate only chains that are **otherwise complete**. Otherwise complete means: **every non-empirical link is proven** (grade A, B, or C) **and the terminal is named**. Empirical unknowns are precisely what the escalation buys, so a chain may hold more than one of them and still be eligible; what disqualifies a chain is an unread readable-unknown, a surviving unfalsifiable-unknown, or no terminal. Escalation is the last construction step, not an exploration tool.
- One escalation in flight per chain: breadth-concurrent across chains, depth-sequential within a chain. A chain with two empirical unknowns is eligible from the start and simply pays for the second only after the first is proven; if the first is refuted the chain dies and the second is never paid for. This is a scheduling rule, not an eligibility rule, and it does not narrow C3.
- A chain may be dropped without escalation when reading settles it false; log it in `Chains abandoned` with the reason. Escalate only load-bearing unsettleable facts, where load-bearing means the finding disappears if the fact goes the other way. Noticing a chain must never be more expensive than not noticing it.
- **Per-file agents never call `/dexter:solve`** [A-D6][E-D7]. They return unproven-fact records (the fact, why reading cannot settle it, which chains depend on it) and stop. The orchestrator collects across all agents, dedupes by proposition, and escalates. Escalating from inside agents makes C3's dedup structurally impossible, because no agent can see another's facts.
- Ordering is load-bearing [E-D7]: **stage 1 per-file, then stage 2 stitch, then fact dedup, then dexter, then merge, tier, report.** Escalating before the stitch burns full investigation loops on facts a completion agent settles by reading.
- Expected volume is 0 to 2 per diff, because most unknowns die first at reading, weakening, or trigger satisfiability.

### Steps 4 and 5: invocation contract and verdict mapping

monk invokes `/dexter:solve` **understand-only**, and maps the verdict it returns back onto the
finding. Both tables are owned by `references/KNOWLEDGE-INTEGRATION.md`: the safety-critical
invocation contract (goal, definition of done, suppressed fix phase, unconditionally suppressed
`knowledge/` write, untouched working copy, read-only local scope, and the consent rule for
remote or another author's resources), and the verdict mapping for `proved`, `refuted`, `blocked`,
and an escalation that did not terminate. Read that file before escalating and do not re-derive
either table here.

## Phase 4a: tier assignment

### No confidence decimal [B-D1]

monk never produces a confidence number **in its report output**. The one numeric `confidence` monk
ever writes is the KB frontmatter field, which `kb.py` requires; it is a fixed lookup off the
`## Verification` label, given by the `### Verification vocabulary` table in
`references/KNOWLEDGE-INTEGRATION.md`, which owns both of its values. It is never a judgment about
how sure monk feels, and it never appears in a report.

Each link is annotated:

| Annotation | Meaning |
|---|---|
| READ | a `file:line` monk actually read this session |
| INFERRED | library, framework, or convention semantics not read |
| ASSUMED | a runtime, config, deployment, or scale fact |

Tier is a deterministic lookup over the annotation vector plus two booleans (trigger named,
failure observable). The 0.8 and 0.5 thresholds survive in `SKILL.md` as tier **definitions** only;
no decimal is ever printed or asked for. A reader can audit an annotation; a reader cannot audit
"0.72". `diff_review_bot/tasks.py:130-136` asks for a "confidence score (0.0 to 1.0)" with zero
rubric and `functions.py:122` then hard-filters on it. That is the defect monk exists to fix, not
a mechanism to copy.

### The four properties that move a finding [B-D2]

Each requires a citation.

| Property | Up | Down |
|---|---|---|
| Mechanism grounding: is every link READ? | converting an INFERRED link to READ | an unread link |
| Reachability: is there a cited caller path from an actually-invoked entry point to the defect site? | citing the path | no path found |
| Trigger realism: is the firing condition named, and does a config, test, or call site monk read satisfy it? | naming a real config that satisfies the trigger | a trigger reachable only in a config monk cannot locate |
| Failure observability: hang, crash, wrong value, data loss, leak, versus mere cost | a terminal on the closed list | a cost with no incorrect result |

These are the four things that were load-bearing on D114284934: the exception hierarchy (READ, in
an untouched file), the rank-0-only path (reachability), OOM under a 35B gather (trigger), and
cluster hang (observable).

### The tier lookup [B-D3]

| Tier | Rule |
|---|---|
| **Must Fix** | all links READ + reachability cited + trigger named and satisfiable + failure observable + 0 residual ASSUMED |
| **Human Judgment** | all **other** links READ + trigger named + failure observable, but significance rests on exactly 1 ASSUMED fact no experiment can settle (which configs run, real scale, upstream validation owned elsewhere, author risk tolerance); or an escalation returned `blocked` or unsettled. "All other" is load-bearing: the single residual ASSUMED link is the one thing this tier permits, so requiring *all* links READ alongside it would make the row unsatisfiable |
| **Decisions to Validate** | no defect chain, but a named rejected alternative and a real trade-off, at a file plus symbol anchor |
| any INFERRED link | do not tier. Enter Phase 3.5 triage (read it, escalate it, or kill it). **Single exception, B-D8:** an escalation that returned `blocked` or did not terminate leaves the link INFERRED; that finding is tiered Human Judgment, marked `escalated, unsettled`, with the blocker displayed, and the link consumes the chain's single residual slot |
| everything else | not reported |

An anchor is required in all three tiers, not just Human Judgment. It costs nothing and kills the
vaguest findings.

### The reporting floor [B-D4]

Three structural drop rules, no numbers:

1. No anchor (file plus enclosing symbol) -> drop. It is not actionable.
2. No observable failure **and** no named rejected alternative -> drop. It is a feeling.
3. The "why it might be fine" sentence would read identically on a different finding ("may be intentional", "worth double-checking") -> drop. A generic hedge is the dumping-ground tell.

Plus an explicit prohibition in `SKILL.md`: **never emit a finding so the report is not empty.**
Clean is a valid, expected verdict.

### Gates that keep Human Judgment from becoming a dumping ground [B-D5][F-D4]

1. **Escalation duty.** Factual uncertainty may not rest here. Human Judgment means "mechanism proven, significance unproven", never "I did not check".
2. **Decisive question.** Every item names the one fact that would promote it to Must Fix or delete it, **plus who can answer it** (author intent, product decision). "A reviewer should double-check" is not a settler and the item is deleted.
3. **Hard cap of 3**, enforced by displacement: a 4th must beat and evict an existing one, never append.
4. **No laundering.** A style, naming, or convention observation re-labelled "maintainability risk" or "readability concern" is still out of scope per Non-goals.
5. The census calibration ships inline so hitting the cap is exceptional, not routine.

### Why the tiers do not collapse under C3 [B-D6]

Escalation removes only half the band.

| Uncertainty type | Example | Fate |
|---|---|---|
| A: factual | "does this `except` really let an OOM through?" | Decidable. Must escalate. Exits the band in both directions: proved to Must Fix with proof cited, or killed |
| B: judgment | mechanism fully readable, but whether it *matters* depends on which configs are real, production scale, upstream validation owned by another team, or the author's risk tolerance | Nothing to run. Stays |

Post-escalation, Human Judgment is exactly type B. Both author-confirmed D114284934 findings were
type B: readable mechanisms, deployment-dependent significance. Collapsing type B into Must Fix
would produce exactly the 7.7% red-tier false positives the census already measures.

### Caps and overflow

| Tier | Cap | Enforcement |
|---|---|---|
| Must Fix | none | tripwire, below |
| Human Judgment | 3 | displacement, ranked by terminal severity |
| Decisions to Validate | 3 | displacement, ranked by terminal severity |
| Pre-existing (not this diff) | 3 | displacement; never counted in the verdict |

Evicted items go to the persisted ledger, and the report prints a count-only footer.

Must Fix carries no cap but does carry a tripwire: more than 2 Must Fix items on one diff triggers
a re-verification pass before the report is delivered. Against 18 real critical catches across 929
diffs, three provable Must-Fixes on a single diff is far more likely to be rubric drift than a
genuinely broken diff.

## Phase 4b: persist

Classify every surviving finding against the previous version, then write the per-diff ledger.
`references/PERSISTENCE.md` owns the ledger location and schema, the stable identity used for
cross-version matching, the version-over-version classification, and the single-writer rule that
keeps fan-out from producing two ledgers for one diff. Uncommitted mode writes no ledger [C-D9].

## Phase 4c: ask

Interactive runs close the loop with **one batched prompt** covering every finding whose outcome
monk cannot observe for itself. `references/PERSISTENCE.md` owns the ask protocol: what may be
asked, the once-per-version-pair guard against re-asking, and how a `declined` answer is detected
and suppressed on later versions.

## Phase 4d: report format

`references/REPORT-TEMPLATE.md` owns the exact output structure, the fields required even when
nothing is found, the count-only withheld footer, and both worked examples reproduced verbatim. A
clean report is long, not empty: it is where monk demonstrates work, which removes the incentive
to demonstrate work via a finding [F-D2].

### Verdict mapping [F-D3]

| Must Fix | Human Judgment | Any file unreviewed | Verdict |
|---|---|---|---|
| 0 | 0 | no | `Clean` |
| 0 | 0 | yes | `Clean (partial: N files unreviewed, listed)` |
| 0 | >= 1 | either | `Needs Discussion` |
| >= 1 | any | either | `Needs Fixes` |

`Decisions to Validate` and `Pre-existing` may be non-empty and the verdict is still `Clean`. The
mapping is stated as a table because ambiguity is exploitable: a model reluctant to say Clean can
otherwise park one item in Decisions to Validate and claim Needs Discussion.

## Phase 4e: knowledge capture

`references/KNOWLEDGE-INTEGRATION.md` owns the router that sends a confirmed finding either to
`knowledge/<slug>.md` or to `LESSONS.md`, the ownership rule for findings that were escalated, the
frontmatter mapping, the environment block, the body sections, and what to do when `kb.py validate`
rejects an entry. Nothing is banked from an unconfirmed finding.

## Delivery

**Phabricator-read-only, not read-only.** monk never calls `meta phabricator.diff update`, never
posts inline comments, never emits CI signals, never accepts or requests changes. It **does** write
to `~/workspace/investigations/`: the findings ledger under `reviews/`, and `knowledge/` or
`LESSONS.md` entries per C2 [C gap].

Disclosure, per ADR-0003: a skill labelled read-only still auto-commits to
`~/workspace/investigations` on every review run, without asking, under the commit rule owned by
`references/PERSISTENCE.md`.

| Mode | Behavior |
|---|---|
| default | report to the terminal |
| `--gchat` | pipe the report to `meta google.chat.message send --to=anshulverma --stdin` |

One call. `--to` takes a unixname directly, so no DM-space lookup is needed [C5].

### KB writes in non-interactive modes [C-D7]

**This is the single normative statement of the rule.** Every other site that mentions it (Out of
Scope, Verification item 20) restates it and must not be read as a broader prohibition.

**Non-interactive modes defer the Asked tier; they do not suspend KB writes.** `--gchat` is a
delivery channel, not a reduced-authority mode, and the same applies when monk runs as a spawned
agent. The rule splits by which C2 tier the write comes from, because only one of the two needs a
human at the keyboard:

| C2 tier | Needs user input | Behavior in `--gchat` and sub-agent runs |
|---|---|---|
| **Observed** (the persisted predicate is falsified at the anchor across versions) | no | **The write proceeds normally**: `knowledge/<slug>.md` or `LESSONS.md` per the D-D1 router, then `kb.py validate`, `kb.py index`, and the investigations commit. Nothing about it requires a terminal |
| **Asked** (a confirmation only the user can give) | yes | **Deferred.** The finding's `ask:` block records `answer: unanswered`, the ledger gains `pending_ask: true` naming the finding and the question, and no `knowledge/` entry is written for it |

The report states how many confirmations are pending. The next interactive run picks the
`pending_ask` records up through the ordinary batched ask of Phase 4c, subject to C-D6's
once-per-version-pair guard, so deferring loses nothing and re-asks nothing.

Blocking the Observed tier here would be a real loss, not a safety measure: an Observed-tier
confirmation is the one path where monk learns something without spending the user's attention, and
`--gchat` is exactly the mode a scheduled or unattended run uses.

## Out of Scope

- Any Phabricator write: comments, inline notes, signals, accept/reject, `meta phabricator.diff update`.
- Style, naming, formatting, and convention findings, including ones relabelled as maintainability or readability concerns.
- Producing or consuming a confidence decimal in report output. The KB `confidence` frontmatter field is written by fixed lookup and is not report output.
- Lens-based fan-out at any level, including inside an owner agent.
- Splitting one changed file across two agents.
- Cross-diff open-end stitching under `--stack`.
- Persisting uncommitted working-copy reviews, and any Observed-tier KB write from them.
- **Asked-tier** KB writes from `--gchat` or sub-agent runs: they are deferred as `pending_ask` records. Observed-tier writes are explicitly **in** scope in those modes, per the normative rule in Delivery.
- Writing a degraded `knowledge/` entry to satisfy C2 when `kb.py validate` fails.
- Writing `status: provisional` KB entries, in any circumstance, including a verbal corroboration the user insists on banking.
- Reviewing bot-authored or codemod diffs without `--include-bots`.
- Call-graph or component-based partitioning, scripts, or any non-markdown artifact in the skill.

## Agent response schema

### Response schema (parsing contract)

`SKILL.md` and `references/FANOUT.md` share these exact headers [E gap: no agent response schema].
An agent returns compact structured records with no file bodies and no quoted hunks beyond cited
lines.

```
### COVERAGE
file: <path> | status: reviewed | skipped-with-reason: <reason> | partial: <what was not reached>

### DELTA
<2-3 lines: the behavioral delta of this file, feeding the diff-global EXTRA/MISSING check>

### CHAINS
id: <local id>
anchor: <path> :: <symbol>
root: <observation in the changed lines>
links:
  - grade: A|B|C|D | edge: entails|enables | side-condition: <named or none> | annotation: READ|INFERRED|ASSUMED | cite: <path>:<line>
terminal: T1..T6 | <one line>
trigger: <conjunction of side-conditions>
trigger-satisfiability: <config/callsite that satisfies it, or NOT FOUND>
predicate: <one falsifiable sentence about the new code>
negation-checked: <the falsifier and why it does not hold>
decisive-question: <the one fact that promotes or deletes> | settler: <who>
tier: NOT ASSIGNED          # stage-1 agents always. Stage-2 agents emit `PROPOSED <tier>` instead

### OPEN-ENDS
direction: EXPORT | symbol: <sym> | at: <path>:<line> | property: <F now produces/permits X; consequences outside F unknown>
direction: IMPORT | symbol: <sym> | at: <path>:<line> | property: <my chain fires only if Y holds outside F>

### UNPROVEN-FACTS
fact: <proposition, falsifiably worded>
why-unreadable: <what execution/measurement/runtime state it needs>
depends: <local chain ids>

### ABANDONED
chain: <one line> | killer: grade-E-root | unsatisfiable-trigger | negation-held | two-residual-unknowns
```

## Open calibration questions

These values are binding today. Each names what would change it.

- **Human Judgment cap = 3**, enforced by displacement. Record the pre-cap count every review; the report's withheld-count footer is that record. If pre-cap counts routinely exceed 3 across roughly 20 reviews, the rubric is too loose, not the cap too tight. No measurement exists today to justify any other number.

