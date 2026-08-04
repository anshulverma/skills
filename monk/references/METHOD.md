# monk: method

The vocabulary the rest of the monk skill cites by name. Warrant grades, edge kinds, trigger
derivation and satisfiability, the closed list of terminal classes, the stop rules, the chain-root
rule, the negation test, the residual-unknown bound, the chain predicate, and the killer vocabulary
are defined here. Every other monk file names these terms and points back at this file rather than
restating them, because a second copy of a normative table is how the two copies drift apart.

## The seven rules

| Rule | Rationale |
|---|---|
| Never fan out by lens | Splits causal chains across agents that each hold one link |
| Fan out by file or subsystem only | Preserves the chain inside one reasoner |
| Read whole files, both versions, including untouched dependencies | The proof is often in a file the diff never touches |
| Runtime and system state are in scope | The clearest measured delta against Devmate and ACR |
| Never drop the 0.5 to 0.8 band; demote it | The confirmed findings lived there |
| A code comment is a hypothesis, not an alibi | The deadlock sat under a comment claiming it prevented deadlock |
| Diff the code against the author's own summary | Names both unclaimed scope and unmet claims |

The rows are numbered 1 through 7 in table order, and that number is the citation handle other
monk files use:

1. Never fan out by lens
2. Fan out by file or subsystem only
3. Read whole files, both versions, including untouched dependencies
4. Runtime and system state are in scope
5. Never drop the 0.5 to 0.8 band; demote it
6. A code comment is a hypothesis, not an alibi
7. Diff the code against the author's own summary

## Where a chain may start [A-D9]

A chain is a rooted, directed sequence of graded links terminating in exactly one terminal class.

A chain root must be either:

1. an observation in the changed lines, or
2. an observation in behavior the change newly depends on (a dependency the diff starts calling, a contract it starts relying on).

Pre-existing defects found while reading untouched dependencies are real but are not this diff's.
They are reported on a separate marked `Pre-existing (not this diff)` line, never as Must Fix, and
never counted in the verdict.

Never build a chain backward from a scary outcome. Backward construction is how a model
manufactures an entry point for a dramatic ending [A-D8].

## Warrant grades

Grades [A-D1] and the evidence each demands [A-D2].

| Grade | What the link is | Citation required |
|---|---|---|
| A | Mechanical: control-flow reachability, type relation, aliasing, call-site contract | `file:line` for **both** endpoints, from a file opened this run. A recalled API is never grade A. |
| B | Documented semantics of a library or API | Path to the in-repo library source (read it when it is in the repo) or a doc URL. Folklore such as "collectives block" is not a citation. |
| C | Quantitative | The arithmetic (`numel x dtype-bytes x copies`) **and** the denominator it is measured against (device memory, step budget, quota). A cost claim with no denominator is grade E, which is exactly how Devmate filed link 1 of the deadlock as a perf nit. |
| D | A named, decidable runtime condition | The proposition written falsifiably, plus the observation that would settle it. |
| E | Anything not classifiable above | Not a link. The chain ends there and the observation is dropped. |

When the diff cites no job or config, take the denominator from the config or test-plan job the
change targets; failing that, from a KB entry's data points. If no denominator exists, the cost
link is grade D, a named condition, not grade C, and it consumes the chain's single
residual-unknown slot.

The warrant-to-annotation crosswalk, which maps each grade onto the READ / INFERRED / ASSUMED
annotations, is owned by `SKILL.md`; cite it there and do not restate the mapping here.

## Edge kinds [A-D1]

Every edge is annotated:

- `entails` - deterministic given its predecessor.
- `enables` - needs a side-condition, **which must be named**.

A narration of `enables` edges with unnamed side-conditions is the canonical monk false positive.
An unnamed side-condition makes the edge grade E.

## Trigger derivation and satisfiability [A-D3]

```
trigger = conjunction of the named side-conditions on every `enables` edge in the chain
```

Derived mechanically from the edges, never written prose-first. Then tested against the repo:

| Result | Action |
|---|---|
| No config, call site, or code path can make the conjunction true (nothing runs this with `world_size > 1`; that flag is never set) | The finding is **dead**: dropped, not demoted, and logged in `Chains abandoned` |
| Empty conjunction | The failure is unconditional |
| Satisfied by a config, test, or call site monk actually read | Trigger realism is established; this is a promotion condition in the tier rubric |

Most invented chains die on satisfiability, and the check costs only reading.

## Closed list of terminal classes [A-D8]

Terminal means a signal observable outside the changed function's own source. The list is closed:

| Class | Terminal |
|---|---|
| T1 | process crash, hang, timeout, OOM-kill, or nonzero exit |
| T2 | wrong persisted or emitted artifact |
| T3 | silent wrong numerics (NaN, dtype, rank divergence) |
| T4 | unbounded resource growth, or a quantified cost regression |
| T5 | trust-boundary, ACL, or PII leak |
| T6 | a dependent's liveness loss (stranded ranks, held lock, leaked connection) |

Stop rules:

- **Stop at the first terminal reached.** Never chain past a terminal for severity ("which wastes 512 GPU-hours"). That is color, not a link, and it must never raise the tier.
- Never chain through a hypothetical future edit.
- An observation that reaches no terminal on the closed list is not a finding.

## Negation test on every link [A-D10]

State the one fact that would make the link false, then check whether the code rules it out. For
"the except clause misses it" the negation is "MitraRuntimeError subclasses RuntimeError, or an
enclosing handler catches it", checked against `exceptions.py:47` and the enclosing `try` stack.
Record the check in the ledger only for close calls, to keep terminal output small.

## Residual-unknown bound [A-D4]

Unproven-link count is bounded at **report time**, after reading and escalation. Chain length is
not bounded: the motivating deadlock is five links, and a long chain of proven links is fine.
During construction any number of unknowns is allowed as hypotheses.

| Residual grade D / ASSUMED links at report time | Outcome |
|---|---|
| 0, terminal reached | Must Fix eligible |
| exactly 1 | Human Judgment, written as `if P, then <chain> -> <terminal>` |
| 2 or more | Not a finding. Dropped and recorded as killed in `Chains abandoned` |

**An escalated-unsettled INFERRED link consumes the single residual slot exactly as an ASSUMED link
does.** A chain carrying one is therefore at its bound: it may hold no other residual link of
either kind, and a second one drops the chain.

Residual grade B links that were never opened (INFERRED) must be 0 at report time: they are read,
escalated, or killed in Phase 3.5. **One exception, B-D8:** an escalation that returned `blocked`
or did not terminate leaves its link INFERRED. That finding may be tiered, but only into Human
Judgment, only marked `escalated, unsettled` with the blocker displayed, and only while it occupies
the single residual slot. At the census base rate (~4 to 5 novel catches per 929 diffs) a
two-unknown chain's prior does not clear publication. Verified against the D114284934 chain: one
residual unknown (the OOM), so it publishes as conditional and satisfies the never-drop-the-band
rule.

The bound is per finding. The per-report bound on conditional findings is the Human Judgment cap
of 3 in `SKILL.md`; there is no second cap.

## Every chain carries a predicate

Each surviving chain carries a one-sentence falsifiable assertion about the new code, distinct
from its prose claim, for example: "the `except` in `_health_check` names no base of
`RuntimeError` while `dist.broadcast` sits inside the `try`". The predicate is the cross-version
matching key and is a required field in the report row and the ledger [C-D4].
## Killer vocabulary

Every chain that dies is recorded in `Chains abandoned` tagged with exactly one killer. The list is
closed and the spelling is normative:

- `grade-E-root` - the root observation grades E, so the chain never had a first link.
- `unsatisfiable-trigger` - no config, call site, or code path in the repo can make the derived
  trigger conjunction true, so the finding is dead rather than demoted.
- `negation-held` - the negation test named the one fact that makes a link false and the code does
  not rule it out.
- `two-residual-unknowns` - 2 or more residual grade D / ASSUMED links stood at report time.
- `dexter-refutation` - an escalation returned a verdict refuting a load-bearing fact, so the
  finding disappears.

Killed chains are persisted next to surviving findings, each tagged with its killer, so a re-review
neither re-derives the chain nor pays the same escalation twice [A-D10].

`references/PERSISTENCE.md` carries the second normative enumeration of this same closed list; that
duplicate is deliberate, because the ledger schema has to be readable on its own. `FANOUT.md`'s
`### ABANDONED` schema line and `REPORT-TEMPLATE.md`'s worked examples each carry only the subset
they need. The binding rule is spelling, not coverage: every killer token written in any monk file
must be one of these five strings exactly, character for character.
