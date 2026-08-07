# monk: report template

This file owns the exact report structure for both modes, the fields that are printed even when the
review is clean, the `waypoints:` and `predicate:` fields, the rendered line formats, and all three
worked examples. It defines nothing that another file already defines. The two terminal sets
`T1`-`T6` and `D1`-`D4`, the warrant grades, the edge kinds, the chain predicate, survivorship, and
the killer vocabulary live in `references/METHOD.md`. The quality classes `Q1`-`Q8`, the evidence
bar, the severity order, and the canonical tier names live in `references/QUALITY.md`. The tree, the
subtree states, budgeting, and resume live in `references/SCOPE.md`. The tier lookup, the reporting
floor, the caps and their overflow behavior, the Human Judgment gates, and the Must Fix tripwire
live in `SKILL.md`. Cite them by name; do not restate them here.

The single deliberate exception is `### Verdict mapping [F-D3]` below. It is reproduced
byte-for-byte from `SKILL.md`, because whoever is writing the report has to be able to close out a
verdict without leaving this file, and because a verdict table paraphrased in a second place is a
verdict table that will disagree with itself.

`references/REPORT-TEMPLATE.md` ships this structure plus **all three worked examples reproduced
verbatim from the Worked examples section below**: the clean report, the D114284934
conditional-deadlock report, and the repo-mode report. A clean report is long, not empty: it is
where monk demonstrates work, which removes the incentive to demonstrate work via a finding [F-D2].

## Report structure

The skeleton below is the **diff** report. A repo report reuses these sections and their line
formats but runs in a different order, with two coverage blocks and a resume pointer; that order is
fixed under `## The repo report` further down, and nothing here is restated there.

```
## Intent
<the author's claim, or "none stated">

## Intent vs Implementation
ALIGNED / EXTRA: <unclaimed scope> / MISSING: <claimed but absent>

## Priors
Priors: <N> scanned, <K> applicable (<reason when K=0>)
  [[slug]] §Section - matched identifier `<id>` at <path>:<line>

## Read
changed: <path>, <path>, ...
opened:  <path> (to settle: <which link>)

## Coverage                          # fan-out runs only
| file | owner | status | reason |

## Chains
pushed: <N>   abandoned: <M>
  - <one line> | killer: <reason>

## Escalations                       # omitted when none
  - proposition: <P> | verdict: proved|refuted|blocked|unsettled | case: <dexter case dir>

### Must Fix
n | <path> :: <symbol> (line L) | trigger -> chain -> terminal
    waypoints: <path>::<symbol> (L) -> <path>::<symbol> (L)
    predicate: <one falsifiable sentence>
    proof: <citations, or dexter case>

### Human Judgment
n | <path> :: <symbol> (line L) | concern
    decisive question: <the one fact> | settler: <author intent | product decision>
    why it might be fine: <specific to this finding>
    predicate: <one falsifiable sentence>

### Improvements
n | <path> :: <symbol or heading> (line L) | Q<k> <class name>
    evidence: <present inconsistency | commit <hash> | checkable absence>, cited
    fix: <the named alternative, specific enough to act on>

### Decisions to Validate
n | <path> :: <symbol> (line L) | the author chose X over Y | trade-off

### Outside review scope                 # repo mode only; diff mode uses Pre-existing
n | <path> :: <symbol or heading> (line L) | <one line>   # never counted in the verdict

### Pre-existing (not this diff)
n | <path> :: <symbol> (line L) | <one line>          # never counted in the verdict

## Calibration
prior reviews: <X> findings emitted, <Y> confirmed, <Z> declined (last <W>)
<n> lower-ranked observations withheld                # count only, no content

## Verdict
Clean | Clean (partial: N files unreviewed, listed) | Needs Fixes | Needs Discussion
```

### Emit the report inside a fenced block

The skeleton above is fenced for a reason: continuation lines under a finding carry meaning
through their indentation. Emit the whole report inside a fence with real spaces.

Never substitute HTML entities such as `&nbsp;` for indentation. Markdown renderers pass them
through as literal text, so the reader sees the entity instead of the indent. If a surface
cannot render a fence, drop to flat lines with an explicit `key:` prefix on each continuation
rather than faking the nesting.

### The reader is the monk user, never the diff author

Write every finding in the third person, naming the author as `the author`. Never address the
reader as the person who wrote the code: no "you chose", no "your test plan", no "your MAST run".

This is not a style preference, it is a consequence of Phabricator-read-only. monk never posts a
comment, so the report is delivered only to whoever invoked it, and that person is usually
reviewing someone else's diff. Second person silently asserts that the reader is the author,
which is false by default and reads as a factual error about who did what. The rule covers the
whole report, not just the `Decisions to Validate` row whose schema line is the usual source of
the leak: a body paragraph that slips into "your" is the same defect.

When the monk user IS the author, third person costs nothing.

### Chains: what the report says about abandoned chains

Abandoned chains surface in the report as one line each, carrying the killer. The persisted ledger
carries the full reasoning. This shows the base rate the census demands without turning a clean
review into a wall of rejected speculation.

The killer token on each line is one of the six strings in `references/METHOD.md`'s
`## Killer vocabulary`, spelled exactly. Cap-evicted findings are not abandoned chains: they are
live findings displaced by the caps in `SKILL.md`, and they appear only as the count-only footer
already present in the skeleton above.

A `Q candidates dropped` block is the quality-finding counterpart of `Chains abandoned`, printed
the same way, one line each, carrying the single token `references/QUALITY.md`'s
`## Q candidates dropped` owns. It is never merged into `Chains abandoned`: a dropped candidate was
never a chain, and its token is not a killer.

Required even when nothing is found: Intent, Intent vs Implementation (EXTRA/MISSING may be
non-empty and the verdict still Clean), Priors, Read, Chains, Must Fix: none, Human Judgment:
none, Calibration, Verdict. `Decisions to Validate`, `Improvements`, and
`Pre-existing` are optional in a diff report. **`Outside review scope` never appears in a diff
report at all**: its only admission rule is repo mode's declared-scope test, and
`Pre-existing (not this diff)` is diff mode's counterpart for the same shape of finding. Two
destinations with no rule choosing between them is a contradiction, not a convenience. A repo report additionally always prints
`### Improvements` and both coverage blocks, with `none` where they are empty, because those are
what a repo review is mostly for and an omitted section reads as a tier that does not exist.

### The two new tier sections

Both line formats are owned here and their vocabulary is owned by `references/QUALITY.md`.

`### Improvements` holds quality findings, ranked by the order in `references/QUALITY.md`'s
`## Q severity order`, never scored. Every line carries three things and is dropped without them:
the anchor, the **cited** evidence in one of the three admissible forms, and the `fix`. A fix
specific enough to act on is the contract with whatever applies it, so "call
`shared/paths.py :: resolve_shard_root` instead" is a fix and "deduplicate this" is not.

`### Outside review scope` holds a finding whose anchor lies beyond the declared scope, one line
each, capped by displacement and **never counted in the verdict**. It is where an open end whose
consuming side leaves the scope is closed rather than carried forever. It is named
`Outside review scope` and not "out of scope" because `SKILL.md` already carries an
`## Out of Scope` non-goals heading, and two headings with one name make every citation to either
one ambiguous.

Every Must Fix states a triggering condition. A finding that cannot name what makes it fire is
demoted to Human Judgment, not deleted; a finding whose trigger conjunction is unsatisfiable in
the repo is dropped, not demoted [A-D3].

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

`Improvements` and `Outside review scope` join that list. Neither drives the verdict, exactly as
`Decisions to Validate` does not, and the table gains **no rows and no columns** for repo mode.

**Coverage is a clause on the verdict, not a row in the table.** A bare `Clean` requires full
coverage. An unreviewed file forces `Clean (partial: N files unreviewed, listed)`, and in repo mode
an unbudgeted subtree forces the parenthesised form too, because a deliberate stopping point still
leaves the denominator smaller than the repository. Both qualifiers may print at once, innermost
first:

    Clean (partial: 2 files unreviewed, listed; 4 of 7 subtrees complete)
    Needs Fixes (4 of 7 subtrees complete)

Unbudgeted subtrees and unreviewed files are different things and print in separate blocks: one is
a deliberate stopping point, the other is a failure, and merging them would let either read as the
other. `references/SCOPE.md`'s `## Subtree states` owns the first vocabulary;
`references/FANOUT.md`'s `## Coverage ledger and partial-review honesty [E-D9]` owns the second.

## The repo report

A repo report is a document rather than a terminal blurb. The full report is written to
`reviews/repo-<slug>-report.md` **without frontmatter**, which is what keeps it out of the
calibration window: that glob matches `reviews/*.md` and reads `counts:` from frontmatter, so a file
with none is skipped while the manifest beside it is still read. A **ranked digest** goes to the
terminal, or to `--gchat`, carrying the verdict, the coverage, and the top of each tier under the
global caps.

Sections, in this order:

| # | Section | Content |
|---|---|---|
| 1 | Scope and budget | scope root, `--scope`, `--since`, budget spent of budget available, units reviewed |
| 2 | Intent spine | pass 1's one line per node, ancestors first, inherited lines marked |
| 3 | Coverage | two blocks, never merged: subtree states, then per-file statuses for the units reviewed |
| 4 | Intent vs Implementation | per unit that declared an intent, rolled up: ALIGNED / EXTRA / MISSING |
| 5 | Priors | as in a diff report |
| 6 | Read | files opened **outside** the reviewing unit, with why. Coverage rows are per file inside a unit and have no column for an out-of-unit dependency, which unlimited repo aperture makes load-bearing |
| 7 | Chains | pushed and abandoned, one line per abandoned chain carrying its killer |
| 8 | `Q candidates dropped` | one line per dropped candidate, carrying its token |
| 9 | Escalations | omitted when none |
| 10 | `### Must Fix` | all of them; there is no cap, only the per-unit tripwire |
| 11 | `### Human Judgment` | ranked digest under the global cap, remainder count-only |
| 12 | `### Improvements` | ranked digest under the global cap, remainder count-only |
| 13 | `### Decisions to Validate` | ranked digest under the global cap, remainder count-only |
| 14 | `### Outside review scope` | one line each, under the global cap |
| 15 | Calibration | the outcome window for `mode: repo` only, plus the statement that repo mode's brakes are unmeasured |
| 16 | Verdict | with its coverage clause, per the mapping above |
| 17 | Resume pointer | the exact command that continues this run, plus what it would pick up |

Everything durable is in the per-unit ledgers regardless of what the digest shows, so a
count-only remainder is a display decision and never a loss.

## Worked examples

All three examples below ship verbatim in `references/REPORT-TEMPLATE.md`. They are normative about
**shape**: where a prose rule elsewhere in this spec and an example's structure disagree, that is a
defect in one of them and must be reconciled, not resolved by preference.

### Example 1: a clean report

The expected outcome, at a ~1.7% base rate. Note the shape: `Must Fix: none` and
`Human Judgment: none` are printed rather than omitted; `Priors` names why zero applied instead of
stretching a topical match; and the four abandoned chains each carry a killer, which is where the
urge to report is discharged at no cost to the author. `Coverage` is absent because the diff has
two reviewable files and did not fan out; `Escalations`, `Decisions to Validate`, and
`Pre-existing` are absent because they are empty and optional.

```
## Intent
Add a `--dry-run` flag to `mitra/tools/checkpoint_gc.py` so operators can see which checkpoint
directories would be deleted before deleting them. (D114301882, v2)

## Intent vs Implementation
ALIGNED
EXTRA:   the flag also suppresses the ODS counter bump in `_record_reclaimed`. The summary does
         not claim this. Checked, not a finding: see the second abandoned chain below.
MISSING: none

## Priors
Priors: 7 scanned, 0 applicable (KB is gpu-training-perf / cuda-kernel-debugging; this diff is
        fbcode-python / offline tooling, and no entry's identifier appears in any file read)
Lessons: 23 headings scanned, 0 bodies opened (no heading names a tooling or deletion seam)

## Read
changed: mitra/tools/checkpoint_gc.py, mitra/tools/tests/test_checkpoint_gc.py
opened:  mitra/tools/lib/manifold_client.py (to settle: whether `delete_dir` is still reached on
         the dry-run path)
         mitra/tools/lib/ods.py (to settle: whether the suppressed counter feeds an alert)

## Chains
pushed: 4   abandoned: 4
  - the dry-run path still reaches `delete_dir` through `_reclaim` | killer: negation-held
    (`_reclaim` returns at checkpoint_gc.py:141 before the call, in both versions)
  - suppressing the ODS counter breaks a paging alert | killer: unsatisfiable-trigger
    (no alert reads `checkpoint_gc.reclaimed_bytes`; ods.py:220 registers it as untracked)
  - the flag defaults to true and silently disables real GC | killer: negation-held
    (`default=False` at checkpoint_gc.py:57, and the test asserts it)
  - `--dry-run` with `--force` is contradictory | killer: grade-E-root
    (reaches no terminal on the closed list; this is a UX objection, not a defect)

### Must Fix
none

### Human Judgment
none

## Calibration
prior reviews: 11 findings emitted, 3 confirmed, 2 declined (last 9 reviews)
emission bar: normal

## Verdict
Clean
```

### Example 2: D114284934, the motivating case

The five-link deadlock, rendered as monk would actually report it. Every link carries a warrant
grade, an edge kind, an annotation, and the citation its grade demands. The `enables` edges name
their side-conditions, and the trigger is the mechanical conjunction of exactly those two
side-conditions, not prose written first.

```
## Intent
Add a post-conversion health check to the DCP-to-HF checkpoint converter so a checkpoint that
converted to all-zero tensors is caught before it is published. (D114284934, v1)

## Intent vs Implementation
ALIGNED
EXTRA:   none
MISSING: none

## Priors
Priors: 7 scanned, 1 applicable
  [[fsdp-gather-peak-memory]] §Data points - proved that a full-parameter gather peaks at roughly
  2x the sharded footprint under FSDP; this diff creates that condition at
  mitra/.../convert.py :: _DcpToHfConverter._health_check (line 206). Matched identifier
  `_gather_full_tensor` at convert.py:198
Lessons: 23 headings scanned, 1 body opened (`## 2026-05-12 collective-skew hangs`)

## Read
changed: mitra/.../convert.py, mitra/.../tests/test_convert.py
opened:  mitra/framework/error_classification/exceptions.py (to settle: link 3, whether
         `MitraRuntimeError` stands in any base relation to `RuntimeError`)
         third-party/pytorch/torch/distributed/distributed_c10d.py (to settle: link 5, whether a
         gloo process group carries a device-side watchdog)
         mitra/.../configs/dcp_to_hf_35b.yaml (to settle: trigger satisfiability, and the
         denominator link 1 needs)

## Chains
pushed: 6   abandoned: 5
  - the zero-fraction scan false-positives on a legitimately sparse tensor | killer: grade-E-root
    (reaches no terminal; the check only logs, convert.py:220)
  - the `torch.float32` cast changes the published checkpoint dtype | killer: negation-held
    (the cast feeds only the local `.mean()`; the published tensor is never reassigned,
    convert.py:214)
  - the health check races the writer | killer: unsatisfiable-trigger
    (`_health_check` is called after `_finalize` returns, convert.py:301; no config reorders it)
  - the added test masks the failure by stubbing `dist` | killer: negation-held
    (the stub is scoped to `test_zero_detection`, not to the collective path)
  - `MitraException` swallows the traceback at the caller | killer: dexter-refutation

## Escalations
  - proposition: a gloo process group's default timeout is honored for a `broadcast` whose root
    never contributes | verdict: proved | case: cases/2026-08-04-gloo-bcast-timeout
  - proposition: `MitraException` discards `__cause__` when re-raised at the converter's caller
    | verdict: refuted | case: cases/2026-08-04-mitra-exc-traceback

### Must Fix
none

### Human Judgment
1 | mitra/.../convert.py :: _DcpToHfConverter._health_check (line 212) |
    if the gather ever reaches a scale where the fp32 scan copy exceeds rank-0 headroom, an
    uncaught OOM on rank 0 strands ranks 1-7 in `dist.broadcast` until the job watchdog

    chain, root -> terminal:

    root | convert.py:206-231
         | the new `_health_check` runs a rank-0-only tensor scan AND a collective
         | `dist.broadcast` inside ONE `try` whose only `except` names `MitraRuntimeError`
         | (observation in the changed lines, so a legal chain root)

    L1   | grade C | edge: enables | annotation: READ
         | side-condition: a gathered tensor's fp32 image does not fit rank-0 free HBM at scan
         |   time
         | `(t == 0).to(torch.float32).mean()` at convert.py:214 materializes a full fp32 copy of
         |   each gathered tensor before reducing it. `.to()` on a dtype change allocates; it is
         |   not a view
         | arithmetic: 35B params x 4 B = 140 GB of fp32 image over the gather set; the largest
         |   single tensor's fp32 copy is 9.8 GB (dcp_to_hf_35b.yaml:31, `tp_shard: 4`)
         | denominator: 80 GB HBM per device (dcp_to_hf_35b.yaml:12, `accelerator: H100-80GB`),
         |   of which the resident gather already holds 61 GB at that point
         | (a cost claim without this denominator would be grade E, which is how Devmate filed
         |   this link as a perf nit)

    L2   | grade D | edge: enables | annotation: ASSUMED   <-- the single residual unknown
         | side-condition: a config that actually runs converts at a scale where L1's
         |   side-condition holds
         | NOT escalated, and correctly so: this is B-D6 type B uncertainty. Which conversion
         |   configs are real, and at what scale a team chooses to run them, is a deployment
         |   fact with nothing to measure. Dexter could not settle it either, so escalating
         |   would burn a loop and return `blocked`

    L3   | grade A | edge: entails | annotation: READ
         | `torch.cuda.OutOfMemoryError` is not caught by `except MitraRuntimeError`
         | `MitraRuntimeError(MitraException, RuntimeError)` at
         |   mitra/framework/error_classification/exceptions.py:47 makes `MitraRuntimeError` a
         |   SUBCLASS of `RuntimeError`, not a base of it. The handler therefore catches strictly
         |   less than `RuntimeError` and catches nothing `torch.cuda.OutOfMemoryError` raises
         | negation checked: "`MitraRuntimeError` is a base of `RuntimeError`, or an enclosing
         |   handler catches it" - false at exceptions.py:47, and the enclosing `try` stack
         |   (convert.py:301, then `run()` at convert.py:88) holds no bare `except`
         | coverage: the handler names 1 of the 6 exception types raisable on this path

    L4   | grade A | edge: entails | annotation: READ
         | the uncaught raise exits `_health_check` at convert.py:214, which is BEFORE the
         |   `dist.broadcast` at convert.py:231, so rank 0 never enters the collective
         | the comment at convert.py:210 claims the `try` "prevents a partial-checkpoint
         |   deadlock". A code comment is a hypothesis, not an alibi: the handler it describes is
         |   the mechanism that causes one

    L5   | grade B | edge: entails | annotation: READ
         | ranks 1-7 are already blocked in the matching `dist.broadcast` at convert.py:231,
         |   reached unconditionally on every rank, on the gloo process group built at
         |   convert.py:96. Gloo carries no device-side watchdog, so the blocked ranks are
         |   released only by the job-level timeout
         | cite: third-party/pytorch/torch/distributed/distributed_c10d.py:4412 (in-repo source,
         |   opened this run) + case cases/2026-08-04-gloo-bcast-timeout

    term | T6 | 7 of 8 ranks hold a liveness loss until the 1800 s job watchdog kills the job

    trigger: (a gathered tensor's fp32 image does not fit rank-0 free HBM at scan time)
             AND (a config that actually runs converts at that scale)
    trigger-satisfiability: SATISFIED by mitra/.../configs/dcp_to_hf_35b.yaml (35B, H100-80GB,
             world_size 8), which the diff's own test plan names
    waypoints: mitra/.../convert.py :: _health_check (214)
            -> mitra/framework/error_classification/exceptions.py :: MitraRuntimeError (47)
            -> mitra/.../convert.py :: _health_check (231)
    predicate: the `except` in `_health_check` names no base of `RuntimeError` while
               `dist.broadcast` sits inside the `try`
    decisive question: is `dcp_to_hf_35b` a configuration that actually runs at 35B on 8xH100, or
               is the only real conversion path the 7B one? | settler: the author, or the team
               that owns the conversion configs. Not dexter: there is nothing to measure
    why it might be fine: if every conversion that runs is 7B or smaller, the fp32 scan copy is
               1.9 GB against roughly 19 GB of headroom and the allocation never fails. The
               mechanism is proven either way; only its significance turns on this

### Decisions to Validate
1 | mitra/.../convert.py :: _DcpToHfConverter._health_check (line 206) | the author chose a full
    zero-fraction scan over sampling k elements per tensor | the scan is O(numel) and allocates a
    full fp32 copy, while a k-element sample detects an all-zero tensor with the same certainty
    and no allocation. The summary names the rejected alternative ("sampling felt flaky"), so
    this is a real trade-off with a named alternative, not a defect

## Calibration
prior reviews: 11 findings emitted, 3 confirmed, 2 declined (last 9 reviews)
emission bar: normal
1 lower-ranked observation withheld

## Verdict
Needs Discussion
```

#### Why this is Human Judgment and not Must Fix

This is the example's whole point, and the one an implementer is most likely to get wrong.

Four of the five links are READ with the citation their grade demands, the terminal is on the
closed list, reachability is cited, and the trigger is satisfied by a config in the repo. Every
Must Fix property in the B-D2 table is met except one: **L2 is a residual ASSUMED link**, so the
A-D4 bound puts the finding at exactly 1 residual and the B-D3 lookup returns Human Judgment, not
Must Fix. It is written conditionally, as `if P, then <chain> -> <terminal>`.

L2 stays rather than escalating because of the B-D6 split. The *factual* half of this chain, "does
`except MitraRuntimeError` catch `torch.cuda.OutOfMemoryError`", was a **readable** unknown under
the Phase 3.5 three-way split: it was settled by opening `exceptions.py`, and escalating it would
have been the waste an unlimited budget invites. What remains is *judgment*: whether the configs
that make the cost bite are configs anyone runs. Nothing executes to settle that, so Human
Judgment's escalation duty is satisfied and the item is legitimately type B.

This is also the case the never-drop-the-band rule exists for. A reviewer that hard-filters the
0.5 to 0.8 band drops this entire finding; a reviewer that rounds it up to Must Fix contributes to
the measured 7.7% red-tier false-positive rate. Reporting it conditionally, with the decisive
question and its settler named, is the only outcome that is honest about what was proven.

Note the two things the report does **not** do. It does not chain past T6 to "which wastes 512
GPU-hours", because stop-at-first-terminal forbids buying severity with color. And it does not
raise the tier because the `Decisions to Validate` item points at the same lines; that item has no
defect chain, so it is a trade-off, and trade-offs never lift a neighbor.

### Example 3: a repo-mode report, partial budget

Repo mode's shape, on this repository, stopped by the budget with the root review deferred. What
this example is normative about is the section order, an anchor written as a **heading** rather than
a symbol in a document unit, the two coverage blocks printed separately, the verdict carrying its
coverage clause, and the resume pointer.

The Must Fix and both Improvements cite sentences that really are in the files named, so the example
is checkable rather than invented; the tallies, the priors, and the coverage rows are trimmed for
length. A real run reports whatever that HEAD actually holds.

```
## Scope and budget
scope:  ~/workspace/skills, whole tree, no --scope, no --since
budget: 25 units, 14 spent, 11 remaining at stop
units:  14 reviewed (10 leaf groups, 4 nodes); root review deferred
head:   514fe6a

## Intent spine
skills/           a personal skill library, one subdirectory per skill (README.md)
  docs/           decision records for the skills in this repository (inherited)
  docs/adr/       one numbered ADR per decision, immutable once merged
  monk/           review a diff for real defects (SKILL.md frontmatter)
  sdd/            take a spec to implemented code with minimal supervision (SKILL.md frontmatter)
  auto-plan/      Intent: none stated (inherited: a personal skill library)

## Coverage
subtrees: complete: docs, monk, sdd
          deferred: auto-plan, i-have-adhd
          skipped:  none
          3 of 8 subtrees complete, root review deferred
          open ends pending root review: 2

files:    | file                            | unit           | status     | reason           |
          | sdd/SKILL.md                    | sdd            | reviewed   |                  |
          | sdd/references/LOOP.md          | sdd-references | reviewed   |                  |
          | sdd/references/STAGES.md        | sdd-references | reviewed   |                  |
          | docs/adr/0001-...md             | docs-adr       | reviewed   |                  |
          | i-have-adhd/hooks/always-on.js  | none           | unreviewed | subtree deferred |

## Priors
Priors: 7 scanned, 0 applicable (the KB is gpu-training-perf / cuda-kernel-debugging; this
        repository is skill text, and no entry's identifier appears in any file read)
Lessons: 23 headings scanned, 1 body opened (citation rot in skill text)

## Chains
pushed: 5   abandoned: 3
  - two ticks overlap and dispatch competing units | killer: negation-held
    (LOOP.md:76 states scheduled jobs fire only while the REPL is idle, so two ticks cannot
     overlap, and the same section gives that as the reason no lock file exists)
  - a unit that dies mid-flight wedges the pipeline permanently | killer: negation-held
    (the staleness row under sdd/SKILL.md :: ### In-flight marker clears a marker older than
     30 minutes and redoes that unit)
  - a cron interval under 10m starves the run | killer: grade-E-root
    (LOOP.md:59 rules the interval out already; a preference about pacing reaches no terminal
     on the document set)

## Q candidates dropped
  - monk/references and sdd/references could share one "open calibration questions" file
    | reason: no-evidence-cited (a preference; no inconsistency and no commit cited)

### Must Fix
1 | sdd/SKILL.md :: ## The Tick Contract (line 37) | D1 contradictory rules

    root | sdd/SKILL.md :: ## The Tick Contract, step 4: "Claim the unit: set `in_flight`, then
         | do one bounded unit". Claiming writes run.json before the unit runs
         | (an observation inside the declared scope, so a legal chain root)

    L1   | grade A | edge: entails | annotation: READ
         | sdd/references/LOOP.md :: ## Interruption safety states the opposite rule with no
         |   exception: "Never write `run.json` at the *start* of a tick to 'claim' work"
         | both sentences are normative, both address the same tick, and neither names the other

    L2   | grade A | edge: entails | annotation: READ
         | a reader who follows LOOP.md never sets `in_flight`, which makes step 3 of the same
         |   contract ("if `in_flight` is set and not stale, do nothing and exit") unreachable,
         |   so the concurrency guard the marker exists for is silently off
         | negation checked: "the staleness window reconciles them" is false as a reconciliation.
         |   The 30-minute row under ### In-flight marker answers LOOP.md's stated *reason*
         |   (permanently skipped work) but leaves its *rule* unconditional, so the two
         |   sentences still cannot both be followed

    term | D1 | the reader picks arbitrarily: one choice disables the guard, the other violates
         |    a rule printed in bold

    trigger: a reader implements a tick from both files, which is the only supported way to
             implement one, since SKILL.md points at LOOP.md for loop mechanics
    trigger-satisfiability: SATISFIED; both files are on the normative path of the same skill
    predicate: two normative sentences in this skill give opposite rules for writing run.json at
               the start of a tick, and neither states precedence
    proof: sdd/SKILL.md :: ## The Tick Contract step 4, and
           sdd/references/LOOP.md :: ## Interruption safety, both read this run

### Human Judgment
none

### Improvements
1 | sdd/SKILL.md :: ### In-flight marker (line 62) | Q1 low locality
    evidence: the N places, cited: the in-flight rule is stated in three files, sdd/SKILL.md
    (the schema and the staleness table), sdd/references/STAGES.md :: ## run.json (the field and
    a one-line semantics gloss), and sdd/references/LOOP.md :: ## Interruption safety (the
    prohibition), so changing one rule takes three edits and the Must Fix above is what a missed
    third edit looks like
    fix: keep the schema and the staleness table where they are and have both references cite
    that section by name instead of restating the rule, the way monk's own references do
2 | sdd/SKILL.md :: ## The Tick Contract (line 58) | Q2 drifted duplicate
    evidence: present inconsistency, cited: "the cron is a watchdog, not a pacer" is stated in
    full in both files, and the copies have already diverged on what "already advancing" tests.
    LOOP.md :: ## The cron is a watchdog, not a pacer names the two tests (`updated_at` moved
    recently, or a unit is in flight); the copy here names neither
    fix: cite that LOOP.md section from the contract rather than restating the rule

### Outside review scope
1 | ~/.claude/settings.json :: hooks (line 41) | the hook registration that makes always-on.js run
    lives outside the declared scope, so its consequences here are unreviewed

## Calibration
prior repo reviews of this repository: none (the mode: repo window is empty)
emission bar: normal
repo mode's three brakes (survivorship, the evidence bar, the per-unit caps) are unmeasured, and
the diff census does not transfer
2 lower-ranked observations withheld

## Verdict
Needs Fixes (3 of 8 subtrees complete, root review deferred)

## Resume
/monk --repo ~/workspace/skills
  picks up: auto-plan, i-have-adhd, then the deferred root review
  carries:  2 open ends pending root review
```

#### What to copy from this example

- **Every finding is anchored at a heading**, because every unit here is a document. No line number is load-bearing: the anchor is the heading, the line is a convenience, and the ledger matches on the anchor, which is exactly why an anchor survives an edit that shifts every line in the file.
- **A document terminal drives the verdict.** The repository holds no running code in the units reviewed, and it is still `Needs Fixes`, because a D1 tiers by the ordinary lookup like any T-class chain. A reader who cannot follow an instruction is as real a failure as a hang.
- **The D finding carries no `why_not_yet`.** Survivorship applies to a chain that could have fired; a contradiction does not fire, it is simply true. The field is absent rather than filled in with "not applicable".
- The chain is written out with graded links, a negation test, and a satisfiable trigger, exactly as a T-class chain is. Nothing about the D set is a lighter standard of proof; only the terminal list differs.
- **The two coverage blocks sit under one `## Coverage` section and never merge.** `deferred` is a budget fact and `unreviewed` is a file fact. A reader who cannot tell them apart cannot tell a deliberate stopping point from a crash.
- The verdict carries its coverage clause even though the tally alone would have produced a bare `Needs Fixes`.
- `Q candidates dropped` prints even when it holds one line. It is where the urge to file a preference is discharged at no cost, exactly as `Chains abandoned` is for chains.
- Improvement 1 and the Must Fix point at the same rule from opposite sides, and neither lifts the other. The Q finding is the structural fact that the rule lives in three files; the D1 is the defect that fell out of it. They coexist because a quality finding has no terminal, so it cannot suppress a chain that does.
- The resume pointer names the **command**, what it would pick up, and what it carries. A pointer that only says "run it again" leaves the reader to re-derive the queue.

## Open calibration questions

This value is binding today. It names what would change it.

- **A clean diff report targets under roughly 40 lines**: one line per abandoned chain, one line per file read, with full reasoning in the ledger. Revisit after the first few real runs if the negative space turns out to be the part users stop reading. **This target is for diff reports only.** A repo report is a written document covering many units, it is delivered as a file with a ranked digest to the terminal, and holding it to 40 lines would force exactly the summarization loss the upward record is built to prevent.
