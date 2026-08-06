# monk: method

The vocabulary the rest of the monk skill cites by name. Warrant grades, edge kinds, trigger
derivation and satisfiability, the two closed terminal sets and the artifact kinds they attach to,
the stop rules, the chain-root rule, the negation test, the residual-unknown bound, the chain
predicate, survivorship, and the killer vocabulary are defined here. Every other monk file names
these terms and points back at this file rather than restating them, because a second copy of a
normative table is how the two copies drift apart.

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

In repo mode there are no changed lines, so the declared scope substitutes for them: a chain root
must be an observation **inside the declared scope**. The rule bounds where a finding may be
anchored, never what may be read. Aperture stays unlimited, and a unit may open any file in the
repository at any depth to prove a link.

A finding anchored outside the declared scope is reported on a marked `Outside review scope` line,
capped by displacement at 3, and never counted in the verdict. It is the repo-mode counterpart of
`Pre-existing (not this diff)`, which is inapplicable when everything under review is pre-existing;
`references/QUALITY.md`'s `## Tier names` owns both tokens.

Never build a chain backward from a scary outcome. Backward construction is how a model
manufactures an entry point for a dramatic ending [A-D8]. The rule matters more in repo mode, which
has no changed lines to anchor honest forward construction.

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

## Closed terminal sets by artifact kind

Terminal means a signal observable outside the source the finding is anchored in. There are two
closed sets, one per artifact kind, and a unit is reviewed against exactly one of them [A-D8]:

| Artifact kind | Terminal set |
|---|---|
| code | T1-T6 |
| document | D1-D4 |

**Artifact kind is mode-independent.** It is a property of a file, not of repo mode: in diff mode
each changed file has a kind, in repo mode each leaf group does. The concept, its two values, and
the set each one selects are owned here. `references/SCOPE.md`'s `## Artifact-kind detection` owns
the detection heuristics only, never the concept.

### T1-T6, code

| Class | Terminal |
|---|---|
| T1 | process crash, hang, timeout, OOM-kill, or nonzero exit |
| T2 | wrong persisted or emitted artifact |
| T3 | silent wrong numerics (NaN, dtype, rank divergence) |
| T4 | unbounded resource growth, or a quantified cost regression |
| T5 | trust-boundary, ACL, or PII leak |
| T6 | a dependent's liveness loss (stranded ranks, held lock, leaked connection) |

### D1-D4, documents

The runtime of an instruction document is a reader following it, so a terminal is a signal
observable outside the rule's own text: the reader does the wrong thing, or cannot proceed. Each
class names the evidence it demands, in the same sense the warrant grades do.

| Class | Terminal | Evidence it demands |
|---|---|---|
| D1 | Contradictory rules: two normative statements that cannot both be followed, so a reader picks arbitrarily | both statements, cited, plus why they conflict |
| D2 | Unsatisfiable rule: a rule, row, or condition no input can satisfy, so whatever it was meant to catch is never caught | the rule, plus the argument that its conjunction is empty |
| D3 | Dangling pointer: a cited section, file, flag, or decision record that does not exist, so the reader cannot obtain what the rule requires | the citation, plus the absence |
| D4 | Unstated rule: a rule the document relies on but never states anywhere normative, so behavior is undefined | the reliance site, plus the absence of any definition |

The D set deliberately **excludes** "drifted duplicate table". Q2 in `references/QUALITY.md` already
covers drifted duplicates in any artifact, and a terminal set overlapping the quality classes would
undercut the reason for closing either list.

D findings run the ordinary tier lookup and do drive the verdict. Nothing about a document terminal
makes it advisory: an instruction a reader cannot follow is a defect in the same sense a hang is.

Stop rules, both sets:

- **Stop at the first terminal reached.** Never chain past a terminal for severity ("which wastes 512 GPU-hours"). That is color, not a link, and it must never raise the tier.
- Never chain through a hypothetical future edit.
- An observation that reaches no terminal on the set its artifact kind selects is not a finding.

## Quality findings are not chain terminals

The quality classes Q1 through Q8 are a **finding kind, not a third terminal set**, and the reason
is the stop rule directly above. If a quality class were a terminal a code chain could stop at, a
chain running through a drifted duplicate would terminate there as an Improvement and **suppress the
real T2 or T3 defect downstream of it**. Monk would get worse at its existing job, in diff mode, as
a side effect of adding quality review.

A quality finding therefore carries no links, no trigger, no negation test, no residual-unknown
bound, and no terminal. `references/QUALITY.md` owns the classes, the evidence bar each one must
clear, the severity order, and the drop token; this file owns the two terminal sets. Neither table
has two owners.

One consequence lands in the identity triple: its third element is `terminal_class` **or**
`quality_class`, exactly one present. A chain supplies the first, a quality finding the second, so
the triple stays total and a chain and a quality finding at one anchor do not collide.
`references/PERSISTENCE.md` owns the fields.

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

## Survivorship

The census base rate is measured per diff and does not transfer to a repository, where the code has
already been running. Its replacement is the code's own history. Every chain reaching a **code**
terminal in repo mode carries a required field:

```
why_not_yet: newly-reachable | has-fired | silent
```

| Value | What it asserts |
|---|---|
| `newly-reachable` | the path is new or rarely reached. **Name the condition** |
| `has-fired` | in-repo evidence that it already happened, cited by `file:line` |
| `silent` | the terminal does not announce itself, so years of running are no evidence against it |

The `has-fired` evidence list is **closed**: a retry loop, a workaround comment, a test pinning the
behavior, a guard added later, or a defensive catch. Cite the one you found by `file:line`. "A guard
added later" is established with `git log -S'<guard text>' -- <path>`, a named command rather than an
assertion, exactly as churn is established by a named command in `references/SCOPE.md`. Evidence is
**in-repo only**: no task, SEV, or log search, which would make every finding cost a round trip and
belongs to a different skill.

**`silent` is illegal for T1 and T6.** A crash, hang, or stranded dependent announces itself by
definition, so calling one silent is a category error. Answer `newly-reachable` or `has-fired`, or
drop the chain. Without this rule two reviewers reach opposite verdicts on the same chain.

When none of the three values can be answered:

| Terminal | Unexplained |
|---|---|
| T1 crash, hang, timeout, OOM-kill; T6 a dependent's liveness loss | **drop**, `killer: survivorship-unexplained` |
| T4 unbounded resource growth, or a quantified cost regression | **demote one step**, floored: Must Fix becomes Human Judgment, and an already-Human-Judgment finding is dropped as `survivorship-unexplained`. Spelled out because Decisions to Validate requires a named rejected alternative and Improvements holds quality findings only, so neither is a legal demotion target |
| T2 wrong artifact; T3 wrong numerics; T5 leak | **no penalty**; these hide by construction |
| D1-D4 | **not applicable**; a document defect does not fire, it is simply true |

Code that has shipped for years without crashing is real evidence that a crash trigger cannot
actually be hit: survivorship is the empirical form of the trigger-satisfiability check that already
kills chains in diff mode. The same argument is worthless for a checkpoint written with subtly wrong
numbers, because nobody was looking.

`why_not_yet` is **absent in diff mode**, where new code has by definition not yet had the chance to
fire. In repo mode it is always written to the ledger, and it prints in the report only when its
value is `newly-reachable` or `has-fired`, `silent` being the uninformative default. It never prints
on a killed chain, which carries its killer instead.

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
- `survivorship-unexplained` - a loud terminal with no answer to `why_not_yet`: a T1 or T6 chain
  that cannot say why the failure has never been seen, or a T4 chain already at its demotion floor.

Killed chains are persisted next to surviving findings, each tagged with its killer, so a re-review
neither re-derives the chain nor pays the same escalation twice [A-D10].

`references/PERSISTENCE.md` carries the second normative enumeration of this same closed list; that
duplicate is deliberate, because the ledger schema has to be readable on its own. `FANOUT.md`'s
`### ABANDONED` schema line and `REPORT-TEMPLATE.md`'s worked examples each carry only the subset
they need. The binding rule is spelling, not coverage: every killer token written in any monk file
must be one of these six strings exactly, character for character.
