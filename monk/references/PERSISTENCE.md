# monk: persistence

This file owns the per-diff findings ledger and the repo-mode manifest: where they live, their exact
schemas, the stable identity used to match a finding across diff versions or across commits, the
predicate-based classification of what changed between them, the rename and move fallback, the ask
protocol, how `declined` is detected and suppressed, the single-writer rule, and the auto-commit
convention. `SKILL.md` phases 4b and 4c point here rather than restating any of it.

It defines nothing another file already defines. The terminal sets `T1`-`T6` and `D1`-`D4`,
survivorship, and the chain predicate live in `references/METHOD.md`. The quality classes `Q1`-`Q8`
and the tier names live in `references/QUALITY.md`. The unit and slug derivation and the
subtree-state vocabulary live in `references/SCOPE.md`. Tiers, the annotation vocabulary `READ` /
`INFERRED` / `ASSUMED`, the caps, and the emission-bar rules live in `SKILL.md`. The KB router, the
`confidence` values, and what `kb.py validate` requires live in
`references/KNOWLEDGE-INTEGRATION.md`. Cite them by name; do not restate them here.

The single deliberate exception is the killer vocabulary, enumerated below as a second normative
copy of the closed list in `references/METHOD.md`, because the ledger schema has to be readable on
its own.

## Location and format [C-D1][C-D2]

`~/workspace/investigations/reviews/D<number>.md`, one file per diff. Not `~/.claude/docs/monk/`.

1. `~/.claude` is not a git repo, so a version-over-version store there has no audit trail and is subject to cache and backup cleanup. `~/workspace/investigations` is git-backed with a documented commit-at-every-meaningful-state-change convention.
2. It is the same repo as the KB that confirmed findings graduate into, so provenance is one directory away.
3. `kb.py index` and `kb.py search` only walk `knowledge/` (verified at `kb.py:34`), so a sibling `reviews/` cannot pollute `KNOWLEDGE.md` or search. The directory is index-safe and search-safe.

Markdown with YAML frontmatter, matching the KB and `cases/` conventions. JSON is rejected: monk
is markdown-only with no scripts, so nothing validates or round-trips it; LLM-rewritten JSON
silently corrupts; and `git diff` on a re-serialized JSON blob is unreadable, which destroys the
main reason for putting it in git.

## Repo mode: one manifest, one file per unit

Repo mode reviews units rather than versions, so the store is a manifest plus one findings file per
unit:

```
reviews/repo-<slug>.md          the manifest
reviews/repo-<slug>/<unit>.md   findings, one file per unit
```

`<slug>` and `<unit>` are derived by `references/SCOPE.md`'s `### Unit filenames and the slug`. The
manifest sits directly in `reviews/` so the calibration-window glob below reads its frontmatter with
no change, and the unit files sit one level down, where that non-recursive glob cannot double-count
them. The rendered report is written to `reviews/repo-<slug>-report.md` **without frontmatter**,
which is what keeps a file matching the same glob out of the calibration window.

Manifest frontmatter:

| Key | Content |
|---|---|
| `repo` | the repository under review |
| `repo_root` | the absolute path the declared scope was resolved against |
| `commits_reviewed` | every HEAD monk has reviewed this repository at, in order |
| `head_at_last_review` | the commit the inventory hashes were computed against, so resume can re-check them |
| `last_review` | ISO date of the most recent run. **Required.** It is the calibration glob's sort key, and a manifest without it cannot be sorted at all |
| `subtrees` | `{complete: [...], deferred: [...], skipped: [...]}`, the closed vocabulary `references/SCOPE.md`'s `## Subtree states` owns |
| `inventory` | one row per unit: path, content hash, and rank. A unit whose hash changed returns to the queue on resume, with its ancestors |
| `open_ends` | open ends left unresolved because the root review was deferred, carried across runs and re-presented when it runs |
| `counts` | the outcome tally, same keys as a diff ledger, plus `mode: repo` |

The per-unit files carry findings only, in the same per-finding schema as a diff ledger. Everything
durable lands in them regardless of what the report's ranked digest shows.

`commits_reviewed` **replaces** `versions_reviewed` in repo mode. There are no diff versions to
enumerate, and the commit a review ran against is the thing a later run has to compare itself with.

## The ledger schema

```markdown
---
diff: D114284934
versions_reviewed: [v1, v3]
last_review: 2026-08-04
stack_order: null         # [D..., D...] in order under --stack; null otherwise
counts: {emitted: 4, confirmed: 1, declined: 1, carried: 1, unobservable: 1}
---

## F1
anchor: fbcode/mitra/.../convert.py :: _DcpToHfConverter._health_check
terminal_class: T6
predicate: the `except` in `_health_check` names no base of `RuntimeError` while `dist.broadcast` sits inside the `try`
tier: human-judgment     # one residual ASSUMED link, so not Must Fix; see the worked example
annotations: [READ, ASSUMED, READ, READ, READ]
decisive_question: is dcp_to_hf_35b a configuration that actually runs at 35B on 8xH100?
settler: author, or the team owning the conversion configs
line_at_raise: 212        # report only, NEVER used for matching
proof: {dexter_case: cases/2026-08-04-gloo-bcast-timeout, fact: "...", fact_anchor: "exceptions.py:47"}
status: carried
symbol_churned: false
history:
  - 2026-08-04 v1 raised (human-judgment)
  - 2026-08-05 v3 carried (predicate still true)
ask: {asked_at: null, asked_version: null, answer: unanswered}
pending_ask: false        # set true when an Asked-tier confirmation is deferred by --gchat
pending_kb: false

## F2 (killed)
...
killer: unsatisfiable-trigger
```

### Frontmatter keys

| Key | Content |
|---|---|
| `diff` | `D<number>`, matching the filename |
| `versions_reviewed` | every version monk has reviewed, in order |
| `last_review` | ISO date of the most recent run. The sort key for the calibration window |
| `stack_order` | under `--stack`, the stack's diff numbers in order at the last review; `null` otherwise. Read by the `--stack` predicate rule below |
| `counts` | the outcome tally for this diff. In frontmatter so the calibration window is a header read, not a full parse |

### Per-finding keys

Every key below is written on every surviving finding, with `null` or `false` where it does not
apply, except the four keys whose row states the condition under which they exist at all. A killed
chain carries `anchor`, `terminal_class`, `predicate`, its reasoning, and `killer`.

| Key | Content |
|---|---|
| `anchor` | `<repo-relative path> :: <fully qualified symbol>`. Two thirds of the identity triple |
| `terminal_class` | on a chain: `T1`-`T6` or `D1`-`D4`, the two terminal sets `references/METHOD.md` owns. The third element of the identity triple |
| `quality_class` | on a quality finding: `Q1`-`Q8`, owned by `references/QUALITY.md`. It takes the same slot, and **exactly one** of it and `terminal_class` is present, so the triple stays total |
| `predicate` | the one falsifiable sentence about the new code. The cross-version matching key |
| `waypoints` | the ordered `<path>::<symbol> (L)` citations between anchor and terminal, as `references/REPORT-TEMPLATE.md` defines them. Stored so a stitched cross-file chain is re-checkable at the next version without re-deriving it |
| `tier` | lowercase-hyphenated: `must-fix`, `human-judgment`, `decisions-to-validate`, `improvements`, `outside-review-scope`. The tokens and their report headings are owned by `references/QUALITY.md`'s `## Tier names` |
| `why_not_yet` | `newly-reachable`, `has-fired`, or `silent`, per `references/METHOD.md`'s `## Survivorship`. Required **only** on a chain reaching a code terminal in repo mode; absent on a `D1`-`D4` chain, on a quality finding, on a killed chain, and everywhere in diff mode |
| `fix` | the named alternative, specific enough to act on. Required on **every** quality finding, in the ledger and on its report line. It is the contract with the downstream apply-skill |
| `owned_at` | optional: the tree node that held the chain under the lowest-common-ancestor rule, recorded for audit |
| `annotations` | the per-link `READ` / `INFERRED` / `ASSUMED` vector, in link order |
| `decisive_question` | for a Human Judgment finding, the one fact no experiment can settle |
| `settler` | who can settle that fact |
| `line_at_raise` | report only, NEVER used for matching |
| `proof` | `{dexter_case, fact, fact_anchor}`, or the plain citations when no escalation ran |
| `status` | `carried`, `addressed`, `declined`, or `unobservable` |
| `symbol_churned` | `true` when the predicate still holds but the symbol was heavily edited |
| `history` | one line per version: date, version, what happened, why |
| `ask` | `{asked_at, asked_version, answer}` |
| `pending_ask` | `true` when an Asked-tier confirmation was deferred by a non-interactive run |
| `pending_kb` | `true` when an `addressed` finding could not be written to the KB |
| `killer` | on a killed chain only, exactly one of the six tokens below |
| `reanchored_from` | the previous `anchor` when a rename or move fallback re-anchored the finding |

`proof: {dexter_case, fact, fact_anchor}` exists so a dexter verdict is not re-bought on every
re-review. Re-use the verdict while `fact_anchor` is byte-identical across versions, and
re-escalate only when the anchored fact itself changed.

`pending_kb: true` marks an `addressed` finding whose KB entry could not be written because
`kb.py validate` rejected it. Never write a degraded entry to satisfy C2; report the missing fields
and let the user supply them or route the finding to `LESSONS.md`.

## Killed chains and the killer vocabulary

Killed chains are persisted next to surviving findings, each tagged with its killer (`grade-E-root`,
`unsatisfiable-trigger`, `negation-held`, `two-residual-unknowns`, `dexter-refutation`,
`survivorship-unexplained`), so a re-review neither re-derives the chain nor pays the same
escalation twice [A-D10].

The list is closed and the spelling is normative. This is the second normative copy of the same
closed list in `references/METHOD.md`, and the two must agree character for character:

- `grade-E-root` - the root observation grades E, so the chain never had a first link.
- `unsatisfiable-trigger` - no config, call site, or code path in the repo can make the derived
  trigger conjunction true, so the finding is dead rather than demoted.
- `negation-held` - the negation test named the one fact that makes a link false and the code does
  not rule it out.
- `two-residual-unknowns` - 2 or more residual grade D / ASSUMED links stood at report time.
- `dexter-refutation` - an escalation returned a verdict refuting a load-bearing fact, so the
  finding disappears.
- `survivorship-unexplained` - a loud terminal with no answer to `why_not_yet`: a T1 or T6 chain
  that cannot say why the failure has never been seen, or a T4 chain already at its demotion floor.

## Stable identity [B-D10][C-D3]

```
identity = (path, enclosing symbol, terminal_class OR quality_class)
```

Exactly one of `terminal_class` and `quality_class` is present, so the triple is total and a chain
and a quality finding sharing one anchor do not collide.

**Never `file:line`.** Lines shift between diff versions and would make every carried finding look
new. `anchor: <repo-relative path> :: <fully qualified symbol>` plus `predicate` disambiguates two
distinct defects in the same symbol. In a document unit the enclosing symbol is the nearest
enclosing heading, per the anchor definition in `SKILL.md`. `id: F<n>` is assigned at first sighting, monotonic per diff,
never reused; it is a label, not the match key. `line_at_raise` is stored for the report only and
is explicitly marked as never used for matching.

**Rename and move fallback:** if `path` is gone, search the new version's changed set for the same
symbol plus predicate. Exactly one hit re-anchors (record `reanchored_from`); zero or many marks
the finding `unobservable` and routes to the ask.

## Version-over-version classification [C-D4][D-D9]

Re-evaluate the persisted predicate and the trigger conjunction against the new version. Do not
line-diff the cited `file:line`. "The author fixed it" is not observable; "the defect assertion is
now false at the anchor" is.

The classification is unchanged in repo mode. The predicate is still the matching key and the table
below still decides; only the thing being compared against changes, from the next diff version to
the current HEAD. Suppressions (`status: declined`) are worth more in repo mode than in diff mode,
because the same repository is audited repeatedly and a declined finding would otherwise return on
every run.

| Observation | Classification |
|---|---|
| Predicate false AND the falsifying edit lies inside the anchor symbol AND the named triggering condition no longer holds | **addressed** (C2 Observed tier -> KB candidate) |
| Predicate still true | **carried**, even if the symbol was heavily edited (record `symbol_churned: true`) |
| Predicate false but the edit is outside the anchor | **carried**, re-anchor |
| Anchor symbol or file deleted, or the enclosing path rewritten wholesale, so the predicate is vacuously false | **unobservable** -> ask [C-D5] |
| Later version is a rebase-heavy land commit | **unobservable** -> ask [C-D5] |

Vacuous truth is the single most likely way a predicate-based rule poisons the KB, and C2 already
says silence is never confirmation. Line or hunk matching produces a false `addressed` on every
restack and rebase; every false confirmation becomes a permanent bad KB entry.

A Human Judgment finding the author neither fixes nor declines is carried once. On the second
unchanged re-review it is dropped, and the pattern is logged to `LESSONS.md` as a candidate
false-positive class. Count the carries from the existing `history:` entries; do not add a
frontmatter field for it. C2 holds that silence is never confirmation; symmetrically, a perpetually
ignored finding is evidence about monk's rubric, not about the code.

## `--stack`: which file state the predicate is evaluated against

A finding stays **anchored to the diff where it was raised** and keeps its own
`reviews/D<n>.md`, but its predicate is re-evaluated against **the stack top's file state**. An
author routinely fixes a finding in a later commit rather than amending the flagged one, and
evaluating against the flagged diff in isolation would re-raise a finding the stack already fixes.

The reorder case is decided **conservatively**, because this is the path that permanently poisons
the KB: a false `addressed` graduates to a `knowledge/` entry that no later review revisits, and
C2 already holds that silence is never confirmation.

| Stack state at re-review | Predicate evaluated against | Classification |
|---|---|---|
| Same diffs, same order; the flagged diff still present | stack top | the ordinary C-D4 table applies unchanged |
| Diffs added above the flagged diff, order otherwise intact | stack top | the ordinary C-D4 table applies unchanged |
| The flagged diff's position changed, or a diff between it and the top was dropped, folded, or split | stack top | **never `addressed`.** `carried` if the predicate is still true; **`unobservable` -> ask** if the predicate is false, whatever the falsifying edit looks like |
| The flagged diff is gone from the stack entirely | not evaluated | `unobservable` -> ask |

A reorder makes C-D4's "the falsifying edit lies inside the anchor symbol" untrustworthy: the edit
that falsified the predicate may now sit *below* the flagged diff rather than above it, and without
the ordering it no longer has, monk cannot tell which. Ambiguity therefore falls through to the
Asked tier, which costs one line in an already-batched prompt and cannot write a false
confirmation. `addressed` is reserved for the unambiguous case.

Detection needs no scripts: Phase 0 records the stack's diff numbers in order in each ledger's
frontmatter as `stack_order`, and compares that list against the current order.

## The calibration-window retrieval

The **calibration window** is a second, cheap read over the other ledgers: glob
`~/workspace/investigations/reviews/*.md`, sort by the frontmatter `last_review` field descending,
and read only the frontmatter `counts:` map of each until roughly 20 emitted findings are
accumulated. `counts:` is in frontmatter precisely so this is a header read, not a full parse, and
so it still needs no index file.

The window **filters on `mode`**: a run accumulates only ledgers of its own mode, and a `counts:`
map with no `mode` key is a diff ledger. Repo tallies therefore never pool into the diff-mode base
rate. Without the filter one repo run emitting dozens of findings would swamp a window sized at
roughly 20, and the emission bar would swing on evidence from a different kind of review. The glob
stays unchanged: the repo manifest is `reviews/repo-<slug>.md`, so it matches, carries `last_review`
so it sorts, and is separated by `mode: repo` rather than by filename.

## The ask protocol [C-D6]

A terminal `ask:` block per finding: `{asked_at, asked_version, answer: confirmed | declined | unknown | unanswered}`.

- **The same (finding, version-pair) is never asked twice, full stop.**
- `confirmed` and `declined` are terminal forever.
- `unknown` (the user could not tell) is terminal for that version pair; only a genuinely newer version reopens it.
- `unanswered` (skipped, or no TTY) is not re-asked in the same run and is re-asked at most once per new version.
- Asks are **batched into one prompt at the end of Phase 4**, listing all unobservable findings. Per-finding prompts plus unlimited dexter escalation would make the skill unusable.

Keying the guard on the version pair, rather than on "was asked", is what prevents both infinite
re-asking and never asking again after a real new version.

### Two closed vocabularies, one shared token

`status` and `ask.answer` are separate fields with separate closed vocabularies, and `declined` is
the one token that appears in both. Read them by field, never by token alone:

| Field | Closed set | Meaning |
|---|---|---|
| `status` | `carried`, `addressed`, `declined`, `unobservable` | what monk concluded about the finding at this version. `addressed` is the only status that graduates to the KB |
| `ask.answer` | `confirmed`, `declined`, `unknown`, `unanswered` | what the user said at the batched ask, or that they were not asked |

`status: declined` is the persistent suppression state. `ask.answer: declined` is the single event
that most often produces it, the other being channel (b) below. A finding may therefore carry
`status: declined` with `ask.answer: unanswered`, and that is not a contradiction.

`ask.answer: confirmed` on an `unobservable` finding is the C2 Asked tier. It does not become
`status: addressed`: `addressed` is reserved for a predicate monk itself observed to be false at
the anchor. **Silence is never confirmation**, and neither is an outcome monk could not observe.

## How "declined" is detected [C-D8]

monk never posts the finding, so the author never sees it and the Phabricator comment thread is
not a decline channel. Decline is recorded only when:

(a) the monk user says so during the review or at the batched ask, or
(b) a later version adds a deliberate contradicting assertion at the anchor (a comment or guard that names the concern).

A `declined` finding stays in the file forever as a **suppression**: on every later review monk
matches new candidates against declined anchors plus predicates and does not re-raise them.
Suppression is scoped to the diff. The same claim declined on three separate diffs is a
`LESSONS.md` candidate ("known false positive at this seam"). Suppression is the main day-to-day
payoff of persistence, distinct from the KB path.

This ask-and-suppress layer exists because of what monk is not. monk is **Phabricator-read-only**:
it never calls `meta phabricator.diff update`, never posts inline comments, never emits CI signals,
never accepts or requests changes. It **does** write to `~/workspace/investigations/`. That
asymmetry is ADR-0003, and it is the whole reason the layer is needed: with no comment thread there
is no decline channel, so monk has to ask its own user and remember the answer.

## Single writer [C-D10]

**Single writer, multiple writes.** The top-level monk run is the only process that ever writes
`reviews/D<n>.md`, and in repo mode the only one that writes the manifest or any file beneath
`reviews/repo-<slug>/`, but it writes more than once per run, sequentially:

| Phase | What it writes |
|---|---|
| 4b | classification against the previous version, all surviving findings, all killed chains |
| 4c | the `ask:` block of each unobservable finding, once the batched prompt is answered |
| 4e | `status`, `pending_kb`, and the `knowledge/` or `LESSONS.md` backlink for anything banked |

Per-file and stage-2 agents return findings and never touch the store; concurrent writers on one
per-diff file would interleave partial state. Centralizing the write also lets classification see all findings at once
for dedup. This adds a write step the source spec's Phase 0 to 4 list lacked, and a read step to
Phase 0 (`load reviews/D<n>.md if present, apply suppressions, seed carried findings`).

## Auto-commit

monk commits the findings file to the `~/workspace/investigations` git repo, one commit per review
run, with the message `review: D<n> v<k> - <a> addressed / <c> carried`. A repo-mode run commits its
manifest and every unit file it touched in that same single commit, with the message
`review: repo-<slug> <n> units - <a> addressed / <c> carried`. This matches the repo's
commit-at-every-state-change convention; an uncommitted ledger forfeits the version-over-version
audit that justified choosing a git-backed location in the first place. Tell the user this happens:
a skill labelled read-only that auto-commits to a local repo is a surprise worth naming.

## No ledger in uncommitted mode

Uncommitted working-copy review writes no ledger at all: there is no stable identity, the change is
overwritten continuously, and there is no later version to classify against [C-D9]. `SKILL.md`'s
input-resolution table is the normative statement of which invocation resolves to which persistence
behavior, including the durable `source_refs` rule for a confirmation raised in this mode. Two
consequences land here: an uncommitted-mode finding can reach the KB only through the Asked tier of
C2, never through the Observed tier, since there is nothing to observe it against; and when the
change becomes a `D<number>`, monk starts a fresh ledger file rather than back-filling one.
