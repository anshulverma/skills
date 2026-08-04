# monk: fan-out

The multi-agent protocol. When one reasoner can no longer hold every chain in a diff, this file
decides how many agents run, what each one owns, what it is told, what it must return, and how the
orchestrator merges the returns back into a single report without inventing findings or losing
chains at a file boundary.

This file is the normative owner of the fan-out threshold table, of what counts as a reviewable
changed file, of the nine-block brief template, of the open-end EXPORT/IMPORT ledger and the
stitch, of the dedup key and its tie-break, of the rule that agreement between agents is not
corroboration, of the coverage ledger, and of the execution parameters including the concurrency
cap and the diff-inlining budget. `SKILL.md` states that a cap exists and points here for the
number.

Two vocabularies are cited here and defined elsewhere. Warrant grades A through E, edge kinds
`entails` and `enables`, trigger derivation and satisfiability, the closed list of terminal classes
T1 through T6, the negation test, the residual-unknown bound, the chain predicate, and the five
killer tokens are owned by `references/METHOD.md`. The tier lookup, the reporting floor, the four
gates, the caps, the READ / INFERRED / ASSUMED annotations, and the verdict mapping are owned by
`SKILL.md`. Nothing here restates either set; briefs paste from those sections at assembly time.

## Threshold and unit

| Reviewable changed files | Mode |
|---|---|
| 5 or fewer | one reasoner holds every chain across the whole diff |
| more than 5 | one stage-1 agent per reviewable changed file |

The threshold is counted per diff, not across a stack. Under `--stack` each diff is reviewed
against its own base, and open ends are not stitched across diffs; the prior diff's findings and
open ends carry forward as priors so a chain the next diff completes is recognized rather than
rediscovered.

Never split by lens. A perf agent plus a correctness agent plus a security agent is the exact
failure this skill exists to avoid: it is how a five-link chain ending in a cluster hang gets
filed as a performance nit. That is rule 1 of the seven in `references/METHOD.md`; everything below
is its mechanics, not a second statement of it.

## What counts as a reviewable changed file

**The counting unit is the reviewable changed file, which is narrower than C4's "changed file".**
This is a normative refinement of C4's threshold, not a contradiction of it: C4 fixes the split
unit and the number, and this fixes what is countable.

| Kind of changed file | Counted? | Handling |
|---|---|---|
| Ordinary source file, added or modified | yes | one owner agent |
| Test file | yes | one owner agent. Tests are where an unmet intent claim usually shows |
| Renamed | yes, as one file | one agent owning the old path's call sites plus the new content |
| Deleted | yes, as one file | one agent whose job is the call sites of the deleted symbols |
| `@generated` | no | coverage-ledger row marked `skipped-with-reason`, no agent |
| Vendored or lockfile | no | coverage-ledger row marked `skipped-with-reason`, no agent |

With no scripts, `@generated` and vendored files are recognized by header sniff and path
convention, which is a heuristic. A file wrongly sniffed as generated is silently unowned, which is
the exact failure the per-file split exists to avoid, so a miss here is worse than a wasted agent.
When the sniff is uncertain, count the file and assign an agent.

Generated and vendored files are excluded because an agent spent on one burns a wave slot on
output nobody can act on, while still appearing in the coverage ledger so the exclusion is visible
rather than silent.

## Per file, not per connected component [E-D5]

Per-file, not per-connected-component of the call graph [E-D5]. Component structure is preserved
as metadata (the adjacency block in each brief) rather than as the assignment unit, for two
reasons beyond C4 itself: per-file yields a deterministic coverage ledger with exactly one owner
per changed file, whereas component detection can be wrong and a mis-grouped file is silently
unowned; and monk is markdown-only with no scripts, so a real call-graph partition would have to
be model-inferred, meaning guessed. Accepted cost: neighbors get read by several agents and
duplicate findings appear. Dedup absorbs the duplicates; re-reading is accepted like C3's latency.

## Ownership: accountability, not aperture [E-D1]

The brief states verbatim:

> You own every chain that ORIGINATES in file F. You may read any file in the repo, at either
> version, including other changed files.

Ownership decides who must report; it never limits reading. The brief carries an anti-assumption
clause: never skip a consequence because another agent probably owns that file. Double-reporting
is cheap; a dropped chain is the failure this skill exists to prevent. The skill's own founding
case needed an untouched file (`exceptions.py:47`) to prove the chain, so limiting aperture would
recreate ACR's hunk failure on a new axis.

**Anchor rule.** A finding is anchored at the changed line the author can act on, expressed as
`file :: enclosing symbol`. Untouched evidence lines (an exception hierarchy) are cited as proof,
never as the anchor. A stitched cross-file chain carries **waypoints**: an ordered list of
`file :: symbol (line)` citations between anchor and terminal.

## Brief template: nine blocks [E-D2]

| # | Block | Content |
|---|---|---|
| 1 | Ownership | the two sentences above plus the anti-assumption clause |
| 2 | Intent | Phase 1's record verbatim (the author's claim) |
| 3 | Priors | only the KB entries and LESSONS lines that bite, with their `Generalizable lesson` and `Prevention` inlined plus paths |
| 4 | Diff | the full diff (all files) when small, otherwise a change map plus this file's own hunks |
| 5 | Adjacency | which other changed files reference this file's changed symbols, and vice versa |
| 6 | Method | path pointers to `METHOD.md` and `ANTI-PATTERNS.md`, plus the ~1.7% base rate inline |
| 7 | Rubric | tier definitions from `SKILL.md`'s `### The tier lookup`, warrant grades from `METHOD.md`, annotation definitions from `SKILL.md`'s Phase 4a, pasted into the brief at assembly time from those sections, so merged tiers are comparable |
| 8 | Output contract | the response schema below |
| 9 | Prohibitions | no `/dexter:solve`; no recursive fan-out; no quota; no writes; no tier assignment (stage-1 only, relaxed for stage 2 as noted in the stage-2 brief below) |

Briefs cite paths, never paste file bodies. Anything not shared makes agents incomparable at
merge, tier definitions especially, since the orchestrator must not have to re-derive them.

Block 7 ships the rubric text to agents; this file does not become a third normative copy of it.
The assembly step reads `SKILL.md`'s `### The tier lookup` and Phase 4a annotation definitions, and
`references/METHOD.md`'s `## Warrant grades`, and pastes what it finds there. Block 6 inlines the
`~1.7%` base rate only; the rest of the calibration census stays in `SKILL.md` and is cited, not
restated.

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

The four killer tokens on the `### ABANDONED` line are the subset an agent can reach on its own.
The closed list of five, with its normative spelling, lives in `references/METHOD.md`,
`## Killer vocabulary`.

## Open ends: mandatory, not hopeful [E-D3]

For every changed symbol in its file whose observable contract changed, an agent emits an open end
**even when it files no finding**. Detection is a required output field, not an optional courtesy;
if cross-file consequence is optional to report, file-boundary chain loss returns unobserved and
the report looks clean. An agent may not finish while an open end is unrecorded.

An `EXPORT` says this file now produces or permits something whose consequences outside the file
are unknown. An `IMPORT` says a chain inside this file fires only if something outside it holds.
Both are emitted in the `### OPEN-ENDS` block of the response schema above, and both are read back
by the stitch.

## Stitching: two distinct roles [E-D4]

| Role | Does | Never does |
|---|---|---|
| Orchestrator | bookkeeping only: maintains an in-session markdown ledger of EXPORTs and IMPORTs, matches them on symbol identity plus property, keeps unmatched-but-live EXPORTs as open rather than dropping them | invents a chain, reasons about one, or demotes one **as a judgment call** |
| Stage-2 chain-completion agent | dispatched per matched pair, and per live unmatched EXPORT, scoped to the union of involved files; holds the whole chain end to end; reasons, proposes a tier, and either files or explicitly abandons | spawns sub-agents; calls dexter; assigns a final tier |

Stage 1 is candidate generation. Stage 2 is where cross-file chains are actually held. A
mechanical merge by a context-starved orchestrator is exactly the one-link-per-holder failure the
skill exists to prevent.

**"Never demotes" versus "applies the floor and the caps" is not a conflict.** The orchestrator is
barred from *discretionary* re-rating: it may not read a chain, decide it feels weaker than its
holder claimed, and move it down. It is required to run the mechanical steps, which are a function
of fields the holder already emitted: the deterministic tier lookup over the annotation vector, the
three structural floor rules, and the global volume caps by displacement. A cap eviction and a
floor drop are not demotions; they are the same rule applied to every candidate.

The lookup, the floor, and the caps are all owned by `SKILL.md`, Phase 4a. The orchestrator runs
them; it does not restate or reinterpret them.

**Dispatch.** One stage-2 agent per matched EXPORT/IMPORT pair, plus one per live unmatched EXPORT.
A live unmatched EXPORT is one whose property no stage-1 agent claimed and no stage-1 agent ruled
out; it is dispatched rather than dropped, because an EXPORT nobody imported is the shape of a
consequence in a file the diff never touched. Matching is on symbol identity plus property, never
on `file:line`. The ledger keeps every open end until it is matched, dispatched, or explicitly
closed by an agent that read the consuming side and found nothing.

## The stage-2 brief

Blocks 2, 3, 6, 7, and 8 of the nine-block template are reused verbatim, which is what keeps
stage-1 and stage-2 output comparable at merge. Three blocks are replaced:

| # | Block | Stage-2 content |
|---|---|---|
| 1 | Ownership | "You own exactly one chain, end to end, from `<EXPORT anchor>` to `<IMPORT site>`, or to a terminal you establish yourself. You may read any file in the repo at either version. If the chain does not reach a terminal, abandon it explicitly and say where it died." |
| 4 | Diff | the hunks of every file in the union, plus the diff-wide change map |
| 5 | Adjacency | replaced by the matched EXPORT/IMPORT pair verbatim, both stage-1 agents' cited links and annotation vectors, and both behavioral deltas |

Block 9 differs in exactly one clause: a stage-2 agent **may propose a tier**, emitted as
`tier: PROPOSED <tier>`, because it is the only holder of the complete chain and therefore the only
party that can see cross-file reachability. The proposal is an input, not a decision: the
orchestrator still runs the lookup itself and never raises a proposal, though the mechanical floor
and caps may lower or evict one. Every other prohibition carries over unchanged: no
`/dexter:solve`, no sub-agents, no quota, no writes.

## Stage 2 is sanctioned fan-out under C4

C4 names per-file agents because that is the **split** rule, and a stage-2 agent is
not a split at all: it is neither a lens partition nor a second per-file partition. It is scoped to
one chain over the union of the files that chain crosses, and it exists precisely so that one
reasoner holds a cross-file chain end to end, which is C4's actual intent and this skill's first
goal. A literal reading of C4 that forbade stage 2 would leave the stitch unimplemented and would
rebuild the one-link-per-holder failure at the file boundary instead of the lens boundary, which is
the same defect on a new axis. `SKILL.md` and `FANOUT.md` therefore state the sanction explicitly,
so an implementer does not read C4 narrowly and skip the stitch.

The sanction is bounded by the prohibitions already in the stage-2 brief: one chain per agent, no
sub-agents, no `/dexter:solve`, no final tier. A stage-2 agent that would need to spawn another
agent is evidence the chain was mis-scoped at dispatch, not a reason to relax the bound.

## Dedup [E-D6]

Dedup key, corrected to the line-independent identity of B-D10 and C-D3:

```
(anchor file, enclosing symbol) + terminal class
```

Never `file:line`. Line anchors drift between diff versions and across restacks, which would make
every carried finding look new.

| Situation | Resolution |
|---|---|
| Same key, differing intermediate wording | One finding. Keep the version with the longest fully-reasoned chain; union the citations and waypoints. Exact ties break on fewest residual links, then on earliest anchor, per the three-key ordering below |
| Same anchor, different terminal class | Two findings, cross-referenced |
| Duplicates disagree on tier | That disagreement is itself a stitch case: dispatch a completion agent over the union and let it decide |

**Two agents agreeing does NOT raise confidence.** They are the same model on the same priors, so
agreement is correlated, not independent corroboration. Confidence inflation from correlated
agents would push 0.5 to 0.8 material into Must Fix, directly attacking the calibration section
and the measured 7.7% red-tier false positive rate.

Two halves of the original cross-file question are already settled and are not reopened here:
ownership is the agent owning the **root** file [E-D1], and the merge key is the line-independent
identity above [E-D6][B-D10][C-D3], never `(terminal class + cited link set)` and never `file:line`.

### Tie-break: three keys, applied in order

1. **Longest fully-reasoned chain** [E-D6]. Length is counted in links that carry both a grade and the citation that grade demands. Narration, restatement, and ungraded prose are not length.
2. **Fewest residual links**, counting residual ASSUMED plus escalated-unsettled INFERRED together, exactly as the residual-unknown bound counts them.
3. **Earliest anchor**, meaning the candidate whose anchor sits nearest its own chain root. This key exists only to make the ordering total, so two candidates can never both survive a collision.

Length leads rather than residual count because a longer fully-reasoned chain has already
discharged unknowns the shorter one merely never reached: a two-link chain with zero residuals is
not better-evidenced than a five-link chain with one, it simply stopped earlier, and preferring it
would systematically favor the candidate that pushed less far. Residual count then breaks the real
tie, since it is the field the Phase 4a tier lookup actually consumes. Citations and waypoints are
unioned regardless of which candidate survives, so the tie-break decides presentation and never
discards evidence.

## Who tiers under fan-out [B-D9][E-D6]

Stage-1 agents emit **untiered** chains (`tier: NOT ASSIGNED`) carrying the annotation vector,
decisive question, and citations. Stage-2 completion agents emit `tier: PROPOSED <tier>`. The
orchestrator is the single **final** tier assigner: it applies the deterministic lookup once, to
the merged chain from the holder with the most complete chain, then applies the floor and the
global caps. It never averages tiers between duplicates, never raises a tier because two agents
agreed, and never raises a stage-2 proposal.

Required because reachability is often only decidable at the join (the caller lives in another
agent's file, so a per-file agent can only mark it ASSUMED); caps must be global or ten agents
yield thirty Human Judgment items; and two agents routinely find the same chain from opposite ends.

## Prohibitions in every brief [E-D8]

1. **No recursive fan-out.** An owner agent may not spawn its own sub-agents, and specifically not perf, security, or correctness ones, which would rebuild the failure one level down. Very large files are handled by prioritized passes over changed symbols, not by splitting.
2. **No quota.** Zero findings is the expected outcome for a typical file. Agents are graded on chain completeness and open-end honesty, not on finding count. Without this, twelve agents each produce one nit and the merged report contradicts the base rate the skill ships to calibrate against.
3. **No splitting one file across two agents.** Two agents on one file is a lens split by another name, since the only available second axis inside a file is topic. A very large changed file gets one agent, multiple prioritized passes over its changed symbols, and an explicit coverage-ledger note if it could not finish.

## Coverage ledger and partial-review honesty [E-D9]

One row per changed file:

| file | owner | status | reason |
|---|---|---|---|
| `a/b/convert.py` | agent-1 | reviewed | |
| `a/b/gen_pb2.py` | none | skipped-with-reason | `@generated` |
| `a/b/big.py` | agent-4 | partial | 3 of 11 changed symbols not reached |
| `a/b/util.py` | agent-6 | unreviewed | agent failed twice |

Failed or timed-out agents get **one** retry, then the file is marked `unreviewed`. **The verdict
may not be `Clean` while any file is unreviewed**; it reads
`Clean (partial: N files unreviewed, listed)`. Fan-out converts a crash into a false clean bill,
which is worse than a missed finding because it carries an explicit assurance, and the definition
of done promises "nothing found" only when that is the truth.

The four statuses `reviewed`, `skipped-with-reason`, `partial`, and `unreviewed` are the same four
the `### COVERAGE` schema line emits and the same four `references/REPORT-TEMPLATE.md`'s
`## Coverage` block prints. The verdict mapping that consumes them is owned by `SKILL.md`.

## Execution [E-D10]

- Foreground Task-tool agents with read-only tools pre-granted, run in waves of roughly **8 in flight**. Not background workflow agents, which stall on permission prompts and oversized structured output.
- Returns are compact structured records per the schema above.
- The diff is inlined whole when it is small (order **1500 changed lines**); above that each brief gets a change map (per-file hunk headers and touched symbols) plus its own file's full hunks, and agents pull the rest on demand.
- The concurrency cap is recorded in `SKILL.md` so partial waves are visible in the coverage ledger.

## Open calibration questions

These values are binding today. Each names what would change it.

- **8 agents in flight per wave**, and the diff is inlined whole up to order 1500 changed lines; above that each brief gets a change map plus its own file's full hunks. These are fixed numbers rather than adaptive ones because a stated number beats an implementer's guess and both are cheap to tune. Revisit only when a real diff exceeds one of them.
