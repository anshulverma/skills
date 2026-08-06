# monk: quality

The finding kind monk uses for structural defects, and the vocabulary the rest of the skill cites
by name whenever it says "quality". The eight quality classes Q1 through Q8, the evidence bar every
one of them must clear, the severity order that ranks them, the single drop token, the canonical
tier names with their report headings, and the architecture vocabulary are defined here. Every
other monk file names these terms and points back at this file rather than restating them, because
a second copy of a normative table is how the two copies drift apart.

## What this file does not own

| Owned elsewhere | Owner |
|---|---|
| the closed terminal sets, warrant grades, edge kinds, trigger derivation, the negation test, the residual-unknown bound, the chain predicate, and the killer vocabulary | `references/METHOD.md` |
| which tier a finding lands in, and the floor that drops it before it reaches the report | `SKILL.md` |
| how an Improvements line is rendered into the report, and where the report is written | `references/REPORT-TEMPLATE.md` |
| the per-finding ledger keys, including `fix`, and cross-run matching mechanics | `references/PERSISTENCE.md` |

This file names the tiers. It does not decide them.

## A quality finding is not a chain

No links, no trigger, no negation test, no residual-unknown bound, no terminal, no `why_not_yet`.
A quality finding is an **anchored structural observation with a required citation**: a fact about
how the code is arranged, not a causal argument about what it does at runtime.

The reason is mechanical, and it matters more than the taxonomy. `references/METHOD.md` says **stop
at the first terminal reached.** If a quality class were a terminal a code chain could stop at, a
chain running through a drifted duplicate would terminate there as an Improvement and **suppress
the real T2 or T3 defect downstream of it.** That is monk getting worse at its existing job, in
diff mode, as a side effect of adding quality review.

### But it is still first-class inside monk's machinery

Removing Q findings from the chain vocabulary must not remove them from identity, matching,
ranking, drop-recording, and the agent schema. Each is repaired inside the existing machinery
rather than beside it.

| Machinery | Rule for a quality finding |
|---|---|
| identity | the identity triple's third element is `terminal_class` **or** `quality_class`. A chain supplies the first, a quality finding the second. Exactly one is present, so the triple stays total and two findings at one anchor no longer collide |
| cross-run matching | a quality finding carries a `predicate` like every other finding: one falsifiable sentence about the **structure**, for example "`convert.py:88` and `loader.py:212` both compute the shard count and disagree". This is what makes `status: declined` suppression work, so a declined Improvement stays declined instead of returning on every run |
| ranking and displacement | the Q severity order below is the sort key wherever a rubric elsewhere says "terminal severity" |
| drop record | a `Q candidates dropped` report block, parallel to `Chains abandoned`, with its own closed one-token vocabulary |
| agent schema | a `### QUALITY` block parallel to `### CHAINS`, carrying `anchor`, `quality_class`, `evidence`, `predicate`, `fix` |
| diff-mode scope | a quality finding is admitted in diff mode when its **anchor** lies in the changed lines, which is the same anchor test repo mode applies against the declared scope. The changed-lines chain-root rule cannot apply, because a quality finding has no root |

Three consequences follow, and they are not exceptions:

- A quality finding never enters the tier lookup. It routes to Improvements by construction.
- A quality finding never carries `why_not_yet`. Survivorship is a property of a chain that could
  have fired, and a structural observation has nothing to fire.
- A code chain and a quality finding may share an anchor without either suppressing the other,
  because only one of them terminates.

## The eight quality classes

The cost of a design defect is paid **on the next change**, which is why every class below is
defined by evidence available now rather than by a prediction.

| Class | Quality class | Evidence it demands |
|---|---|---|
| Q1 | Low locality: one logical change requires edits in **3 or more** separated places, where separated means different files | the N places, or a commit that had to touch all of them |
| Q2 | Drifted duplicate: the same fact or logic exists in two or more places and the copies already disagree | both sites and the disagreement |
| Q3 | Leaked implementation: callers depend on what is behind the interface, so the implementation cannot be replaced | the consumer reaching past the interface |
| Q4 | No seam: a behavior cannot be substituted or tested, and no test covers it | the untestable behavior and the absent test |
| Q5 | Boundary does not pay for itself: a shallow module, or an interface with one implementation and no test double | the deletion test result, or the single implementation |
| Q6 | Reimplementation: capability that already exists elsewhere in the repo | the existing thing, by path and symbol |
| Q7 | Wrong altitude: a special case layered on shared infrastructure where generalizing the mechanism would remove it | the special case and the mechanism it belongs in |
| Q8 | Dead code: no reachable caller | the absence of callers, and how that was established |

Q1's threshold is 3 because 2 sites is the ordinary caller/callee pair and would fire on nearly
everything.

## The evidence bar

Every quality finding cites exactly one of three forms:

1. **A present inconsistency** in the artifact: two things that disagree, a consumer reaching past
   an interface, a special case the mechanism should have absorbed.
2. **A real past change that paid the cost**: a commit that had to touch all N places, obtained
   with `git log`, cited by hash.
3. **A checkable absence**: no caller, no test, no second implementation, stated together with how
   the absence was established.

Never a prediction, and never a preference.

This bar is stricter than either source skill. Both `simplify` and `mp-improve-codebase` run on
judgment, and neither requires a citation before a candidate is written down. The bar is what keeps
a quality finding auditable in the same sense a chain is, and it is the single most likely thing
for a future maintainer to relax.

A quality finding has no observable failure and no named rejected alternative by construction, so
`SKILL.md` amends rule 2 of its floor (`### The reporting floor [B-D4]`) into a three-way
disjunction rather than adding a rule beside it:

> No observable failure, **and** no named rejected alternative, **and** no cited quality class with
> its evidence -> drop. It is a feeling.

Left intact, rule 2 would drop the entire Improvements tier before it reached the report.

## Q severity order

Q3, Q2, Q4, Q1, Q7, Q5, Q6, Q8

That sequence is the sort key wherever a rubric elsewhere says "terminal severity": ranking within
the Improvements tier, and displacement when the per-unit or global cap is reached. Correctness-
adjacent boundary defects rank first, cosmetic-adjacent structure last.

## Q candidates dropped

The closed vocabulary is **one token**, and the spelling is normative:

- `no-evidence-cited` - the candidate cited none of the three forms on the evidence bar. It is
  dropped rather than demoted, and recorded in the `Q candidates dropped` report block.

`no-evidence-cited` is **not** a killer. Killers belong to chains, a quality finding is not one,
and a killed chain is the only finding that carries a killer at all. It must therefore never be
written under `references/METHOD.md`'s `## Killer vocabulary`: the invariant gate extracts the
canonical killer list from exactly that heading, so a non-killer filed there fails the gate on
correct work.

Cap-evicted quality findings are **displaced, not dropped**. They stay in the per-unit ledger and
appear in the count-only footer, like every other evicted finding. Only the evidence bar drops a
candidate into this block.

## Tier names

The canonical tokens and the report headings they print under:

| Tier | Ledger token | Report heading |
|---|---|---|
| Must Fix | `must-fix` | `### Must Fix` |
| Human Judgment | `human-judgment` | `### Human Judgment` |
| Decisions to Validate | `decisions-to-validate` | `### Decisions to Validate` |
| Improvements | `improvements` | `### Improvements` |
| Outside review scope | `outside-review-scope` | `### Outside review scope` |

Improvements holds quality findings and, like Decisions to Validate, never drives the verdict.
Outside review scope holds a finding anchored beyond the declared scope and is never counted in
the verdict either.

The list lives here rather than in `SKILL.md` so that `references/METHOD.md` and
`references/PERSISTENCE.md` can cite a tier name without depending on the file that implements the
lookup. `SKILL.md` still owns which tier a finding lands in (`### The tier lookup [B-D3]`) and the
caps that evict from it.

The rendered line format for an Improvements entry is owned by `references/REPORT-TEMPLATE.md`.
It is:

```
n | <path> :: <symbol or heading> (line L) | Q<k> <class name>
    evidence: <present inconsistency | commit <hash> | checkable absence>, cited
    fix: <the named alternative, specific enough to act on>
```

`fix` is required on every quality finding, in the ledger and on the report line. It is the
contract with the downstream apply-skill, and a fix nobody can read is not a contract.

## Architecture vocabulary

Adopted verbatim from `mp-improve-codebase`'s `LANGUAGE.md`. Use these terms and no synonyms. If a
concept is not covered, propose adding it here rather than introducing a name in a finding.

| Term | Meaning |
|---|---|
| module | a unit of code with an interface and an implementation: a class, a file, a package, a service. The boundary is what callers can see against what is hidden |
| interface | the public surface callers depend on: signatures, type contracts, error types, behavioral guarantees. Not internal helper functions, private state, or implementation strategy |
| implementation | everything behind the interface. A good implementation can be replaced without changing any caller |
| depth | implementation complexity divided by interface complexity. Deep hides a lot behind a little, shallow exposes nearly as much as it contains |
| seam | a point where one implementation can be substituted for another without changing callers. Not every boundary is a useful seam, only one where substitution is plausible |
| adapter | a thin translation between a module's interface and an external system's interface. Adapters live at seams and carry zero business logic, only mapping |
| leverage | behavior obtained per unit of interface complexity. High leverage is a small interface unlocking large capability |
| locality | how close together the things that change together are. Low locality is one logical change scattered across many files |

Three principles, each of which is a decidable check rather than a taste:

- **The deletion test.** If this module were deleted entirely, would something like it have to be
  recreated? If not, it is not paying for itself, and its logic belongs inlined into the caller.
- **The interface is the test surface.** If a test must reach past the interface to verify
  behavior, either the interface is too narrow or the test is asserting implementation details.
- **One adapter with no second implementation is a seam nobody uses.** That is speculative
  generality. Keep the direct dependency until the second implementation exists.

Rejected framings, banned in finding text:

| Avoid | Use instead | Why |
|---|---|---|
| "wrapper" | adapter, or shallow module | does not say whether it adds value |
| "helper" | inline it, or name the actual concept | says nothing about what it helps with |
| "utility" | name the domain concept | a junk drawer |
| "manager" | name what it actually manages | hides whether the module is deep or shallow |
| "layer" | seam, or adapter | does not say where substitution happens |
| "service", when not a network service | module | overloaded; reserve it for actual network services |
| "clean architecture" | describe the specific structure | too vague to falsify |

The ban is the same discipline as the normative spelling of the killer tokens: a name that does not
say whether a module is deep or shallow cannot carry evidence, so it cannot appear in a finding
that is required to cite some.

## Where these came from

Q1 through Q8 fold in two existing skills. Nothing was dropped in the fold, and this table is the
proof a maintainer can check.

| Source | Lands as |
|---|---|
| `simplify` reuse | Q6 |
| `simplify` simplification (derivable state, copy-paste with variation, deep nesting) | Q2, Q5 |
| `simplify` simplification (dead code) | Q8 |
| `simplify` efficiency, with a quantified cost and a denominator | T4, unchanged defect path |
| `simplify` efficiency, without a quantification | Q7, or dropped; see the split below |
| `simplify` altitude | Q7 |
| `LANGUAGE.md` locality | Q1 |
| `LANGUAGE.md` depth, deletion test | Q5 |
| `LANGUAGE.md` interface against implementation | Q3 |
| `LANGUAGE.md` seam, "the interface is the test surface" | Q4 |
| `LANGUAGE.md` "one adapter is a hypothetical seam" | Q5 |

**Efficiency splits deliberately.** An efficiency observation that reaches a quantified cost with a
denominator is grade C, is already a T4 defect, keeps that path, and keeps driving the verdict. An
efficiency observation with no quantification is grade E under today's rules and would be dropped
entirely; it is admitted as Q7 **only if** it clears the evidence bar, which for a cost claim means
a cited hot path or a cited repetition count. "This does redundant I/O" with neither is still
dropped, as `no-evidence-cited`.

The vocabulary source is
`/home/anshulverma/.claude/plugins/local/mp-skills/skills/mp-improve-codebase/LANGUAGE.md`.

## Open calibration questions

These values are binding today. Each names what would change it.

- **Q1 fires at 3 or more separated places, separated meaning different files.** 3 is chosen
  because 2 is the ordinary caller/callee pair and would fire on nearly every module. Raise it to 4
  only if Q1 alone dominates the Improvements tier across roughly 20 reviews; lower it never,
  because 2 has a known false-positive mode and 3 does not yet.
- **The severity order Q3, Q2, Q4, Q1, Q7, Q5, Q6, Q8 is asserted, not measured.** It ranks by how
  close a class sits to a correctness defect, which is a judgment about the classes rather than an
  observation about findings. Re-derive it from the ledger once enough quality findings carry
  `addressed` against `declined` to rank the classes by acceptance rate.
- **The evidence bar admits exactly three forms.** Widening it is the single most likely future
  relaxation, because every relaxation looks locally reasonable and each one costs an auditable
  finding. `references/ANTI-PATTERNS.md` records it as a reversal to watch. Widen it only with a
  fourth form that names, in advance, what would falsify a finding citing it.
