# monk: the codebase baseline

A **baseline** is a durable, cited description of the codebase a review is anchored in: how it is
laid out, what its runtime actually does, which defaults bite, and which invariants already hold.
It is generated once, reused by every agent in every later review of that codebase, and refreshed
on a schedule.

This file is the normative owner of the baseline's **location**, its **slug**, its **schema**, the
**generation procedure**, the **staleness rule**, and the **one rule that keeps it from becoming a
laundering channel for unverified claims**. `SKILL.md`'s Phase 0.5 runs it;
`references/FANOUT.md`'s block 10 ships it.

## Why it exists

Measured, on a 21-diff stack reviewed with 28 agents and no baseline: agents independently
re-derived the same untouched-dependency facts, over and over. `AsyncBridge`'s 60s default and its
no-cancel-on-timeout behavior were re-read by five agents. `rollout_buffer.py:142` being a `{e}`
log sink was re-derived by four. `_RPC_EXCEPTIONS` membership, OpenConf raising on unknown keys,
and `later.unittest.TestCase` being an `IsolatedAsyncioTestCase` were each re-derived three or more
times.

That is the cheap half of the cost. The expensive half: agents that did **not** re-derive a fact
graded the link `ASSUMED` instead of `READ`, and two agents reached opposite counts of the same
config set. Under Phase 4a's lookup, an annotation vector is what selects the tier — so a shared
fact that one agent read and another assumed produces **two different tiers for the same chain**,
which then collide at dedup and get resolved by a tie-break rather than by the evidence.

A baseline removes the re-derivation, and more importantly makes the annotation vector *comparable
across agents*, which is the property the merge depends on.

## Location and slug

```
~/.claude/docs/codebase/<slug>.md
```

`~/.claude/docs/` is already the destination for generated docs and is already tracked, so a
baseline written here syncs to every machine without a new tracking entry. Verify coverage once per
new environment with `dotsync2 paths diff`; do not add an entry unless that command complains.

`<slug>` is the anchor path relative to the repository root, with `/` replaced by `-`:

| Anchor | Slug |
|---|---|
| `fbcode/ads/nano/nano_retrieval` | `fbcode-ads-nano-nano_retrieval.md` |
| `www/flib/intern/palisade` | `www-flib-intern-palisade.md` |

The slug is derived from the path and never from the project's name. Two codebases can share a
name; they cannot share a path.

## Resolving the anchor

The anchor is the **deepest directory containing every reviewable changed file** in the diff or
stack, per `references/FANOUT.md`'s `## What counts as a reviewable changed file`.

| Situation | Action |
|---|---|
| One directory contains all reviewable changed files | that is the anchor |
| Files span directories but share a deep parent | that parent, if it is not a top-level directory |
| The deepest common parent is the repo root or a top-level directory | **ask the human for a base path**; do not anchor on `fbcode/` |
| One file sits outside the anchor | it stays outside; note it on its own card as an adjacent boundary and do not extend the anchor to swallow it |

A stack resolves **one** anchor for the whole stack, not one per diff. In the stack this was built
from, 20 of 21 diffs sat under `fbcode/ads/nano/nano_retrieval` and the 21st was a different
author's thrift move in `generative_recommenders/`; the anchor was the former and the latter was
recorded as adjacent.

## The evidence rule

**A baseline claim is context. It is never a chain's warrant citation.**

Every claim in a baseline carries its own `path:line`. An agent that uses a baseline fact in a
graded link cites **the underlying `path:line`, never the baseline document**. Two consequences,
both load-bearing:

- A link resting on a baseline fact is graded on whether the agent **read that line**, exactly as
  if there were no baseline. The baseline tells the agent where to look; it does not discharge the
  reading. An agent that cites `BASELINE.md` in a `cite:` field has produced an ungraded link.
- A stale baseline therefore **cannot manufacture a finding**. It can waste an agent's time by
  pointing at a line that moved, which the agent discovers on the read and reports back. It cannot
  put an unverified proposition into a graded chain.

This is the rule that makes a refresh cadence measured in weeks acceptable rather than reckless.

Baseline facts marked `UNCERTAIN` are usable as **search directions only** and may not appear in a
link at any grade.

## Schema

Frontmatter is required and is what the staleness check reads:

```yaml
---
anchor: fbcode/ads/nano/nano_retrieval
generated: 2026-08-24
anchor_commit: <40-char hash the facts were read at>
facets: [orientation, runtime, config, model, subsystem, data, testing, programme]
---
```

Then, in this order:

| Section | Content |
|---|---|
| `## What this codebase is` | Three to six lines. What it does, for whom, what it produces. No history. |
| `## Map` | One table: directory, what lives there, the one file to read first. |
| `## Entry points` | How it is invoked: binaries, targets, launch paths. One line each, with the target. |
| `## Mechanisms` | The runtime behaviors a reviewer must know: threading, async, retry, timeout, lifecycle. Each with `path:line`. |
| `## Defaults that bite` | Table: setting, default value, what it does when nobody changes it, `path:line`. This is the highest-value section. |
| `## Invariants already held` | What the code already defends against, so nobody reports it as a finding. Each with `path:line`. |
| `## Gotchas` | Things that look wrong and are not, and things that look fine and are not. Each with `path:line`. |
| `## Vocabulary` | Table: term, what it is. Domain acronyms and in-repo coinages only. |
| `## External boundaries` | Table: service, transport, what identity is presented, where the address comes from. Omit if the codebase calls nothing. |
| `## Testing` | How to run tests, the real target names, and **which targets are already red at the anchor commit**. |
| `## Programme context` | Ownership, oncall, the docs that exist, with URLs. Sourced or omitted. |
| `## Uncertain` | What was searched for and **not** found, so the next agent does not re-search it. Search directions only; never citable. |

Two sections earn their place by having prevented a specific error:

**`## Testing` naming already-red targets.** Without it, an agent that runs a target and sees it
fail attributes the failure to the diff. Recording the pre-existing failures at the anchor commit
makes that attribution checkable.

**`## Uncertain` recording negative results.** A search that found nothing is a real result and
costs real time. Eight agents each re-searching for a SEV that does not exist is eight wasted
searches; one line saying "searched SEVs for GR, nano, generative retrieval, memcache — none
found; treat as absence of evidence" is the fix.

## Generation

One agent per facet, dispatched in a single wave under the same concurrency cap as a review, per
`references/FANOUT.md`'s `## Execution`. Facets are derived from the tree, not fixed: read the
anchor's top-level directories and its own docs first, then assign one agent per coherent
subsystem, plus these four which are always present:

| Always-present facet | Owns |
|---|---|
| orientation | map, entry points, vocabulary, the codebase's own docs |
| testing | how to run tests, real target names, **and the already-red set** |
| config | how configuration is expressed, whether an unknown key raises or is silently dropped, every launch path |
| programme | ownership, oncall, wikis, design docs, external URLs |

Every generation agent gets the same output schema and these three instructions:

1. **Cite `path:line` for every claim.** A claim without one goes in `## Uncertain`.
2. **Run things.** Build a target, run a test, invoke the CLI, read a config as the loader would.
   Record what you ran under `VERIFIED BY RUNNING`. A codebase described only by reading is a
   codebase described by guessing.
3. **Report what you looked for and did not find.** Negative results go in `## Uncertain` with the
   queries you used.

The programme facet uses the knowledge-search path for wikis, docs and ownership; the others read
and run code. Synthesis is done by the orchestrator: facet reports are merged into the schema
above, and a claim two facets disagree on is resolved by reading the cited line, never by
preferring the longer report.

**Generation writes one file and nothing else.** It does not open a diff, run a review, or write
to `~/workspace/investigations/`.

## Staleness

The baseline records the commit its facts were read at. The check is a date comparison, run in
Phase 0.5:

| Age of `generated` | Action |
|---|---|
| ≤ 30 days | use it; print the age in the report header |
| 31–90 days | use it; print the age **and** a one-line staleness warning in the report header |
| > 90 days | regenerate before reviewing |
| absent, or anchor has no baseline | generate it before reviewing |

`--refresh-baseline` forces regeneration at any age. `--no-baseline` skips both the check and
block 10, for the case where the anchor genuinely has no shared context worth building.

Age is a proxy and is deliberately a weak one. The evidence rule above is what makes a weak proxy
safe: a stale baseline misdirects a read, it does not corrupt a grade. Do **not** replace this with
a commit-count check that requires an O(repo) log scan.

**A refresh is a regeneration, not an edit.** Re-run the facets and overwrite. A hand-patched
baseline has no anchor commit that its facts were collectively read at, which is the one field the
staleness check depends on.

## How it reaches an agent

`references/FANOUT.md`'s brief template gains **block 10, Baseline**, whose content is a path and a
conditional, never a paste:

```
Read ~/.claude/docs/codebase/<slug>.md in full before you read any code. It describes this
codebase as of <anchor_commit>, <N> days ago. Its `## Defaults that bite` and
`## Invariants already held` sections tell you what you do NOT need to re-derive.

Cite the underlying path:line for anything you use from it, never the baseline itself. If a
line it cites has moved, say so in your COVERAGE block.
```

Block 10 is present in both diff mode and repo mode and is identical in both. When
`--no-baseline` is set, or the anchor has no baseline and generation was declined, the block is
**omitted entirely** rather than shipped empty: an empty block reads as "there is no shared
context", which is a different claim from "shared context was not loaded".

The response schema gains one optional line, emitted only when it fires:

```
### BASELINE-DRIFT
claim: <the baseline claim> | now: <what the line actually says> | cite: <path>:<line>
```

**Drift means the baseline is wrong at its own anchor commit. A line the diff under review moves
is not drift.** The distinction is load-bearing and agents get it wrong by default: a diff that
inserts a config block shifts every citation below it, and reporting those shifts as drift both
buries the real records and would trigger a pointless regeneration. Two tests, and the record is
emitted only if both pass:

| Question | Emit a drift record? |
|---|---|
| Is the baseline's claim false when read at `anchor_commit`? | **Yes** — this is drift |
| Is it true at `anchor_commit` but false at `D<n>` because the diff changed it? | **No** — that is the diff doing its job. It belongs in `### CHAINS` or `### DELTA` |
| Is it true at `anchor_commit` but false at `D<n>` because a *different* diff in the stack changed it? | **No** — that is a stack fact. Put it in the `still-true-at-stack-top` field of the chain it bears on |

The orchestrator collects genuine records and prints them in the report footer. Three or more in
one review is the signal to regenerate regardless of age.

**A line-number shift with unchanged semantics is the lowest-value drift record there is.** Prefer
anchoring a baseline claim on `file :: symbol` rather than `file:line` wherever the symbol name is
stable, for the same reason the dedup key is line-independent: line anchors drift on every restack,
and a baseline that has to be regenerated because a config block moved is a baseline nobody will
keep current.
