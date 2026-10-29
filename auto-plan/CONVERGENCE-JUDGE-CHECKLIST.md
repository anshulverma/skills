# Convergence Judge Checklist

You decide whether the hardening meta-loop has **converged** and should stop. You are dispatched
after a pass. Be rigorous and concrete.

## Your Job

You are given two artifact sets — the **snapshot** (pass N-1, the pre-overwrite copy) and the
**current** artifacts (pass N) — plus the Pass agent's self-reported Material Change Assessment
and the **Settled Decisions Log**. Read the log first.

**Independently diff** the snapshot against the current artifacts and classify every change
yourself. The Pass agent's self-report is only a cross-check; if it disagrees with your diff, trust
your diff and note the discrepancy in your Rationale. Never trust the summary in place of looking.

Your prompt names your **scope**. `full`: read every task of the plan (every section of the spec
when there is no plan) in full, not only the text this pass changed. `scoped`: check only the
text the last pass changed. A scoped judgment may report gaps but never `CONVERGED`.

## What to Check

At any scope:

- **Settled decisions**: a finding that would change a logged decision is not a gap. List it
  under Reopens as `reopen: <#>` with the code (`file:line` at the base revision) or spec text
  that shows the decision wrong; without that evidence, drop it. A diff that changed a settled
  decision with no accepted reopen is an `inconsistency` gap: restore the entry's text.
- **CLI usage**: check every command, subcommand and flag against the tool's `--help` (or its
  source) before calling it right or wrong.
- **Rationale**: never report missing rationale or ask to add it. A step needs a reason only where
  it would otherwise look wrong.

At full scope, beyond the diff:

- **Literal executability** (plans): for every step that runs a command or test, every required
  flag, argument and input path is named, and each input is produced by an earlier step or a
  recorded value. A step that fails this is a `blocks-execution` gap.
- **Spec coverage** (plans): every spec step and acceptance criterion maps to a task. An unmapped
  one is a gap.
- **Grounding**: check at least 10 `file:line`, signature and flag claims (all of them if fewer)
  against the source at the base revision the artifacts name. Each wrong one is a gap.

Tag every open gap with its severity: `blocks-execution` (an implementer cannot carry the step
out as written), `inconsistency` (two parts of the artifacts disagree), or `cosmetic`; and with
where it sits: `changed` (in text the last pass changed) or `untouched`.

## Classification Rubric

**Material change** — any diff that:

- adds, removes, or alters a decision;
- changes scope (adds or drops a requirement or task);
- changes an interface, type, signature, or schema;
- adds, removes, or alters an edge case or its handling;
- resolves or introduces an `UNRESOLVED:` marker;
- adds, removes, or alters an ADR or its decision;
- changes a numeric threshold, limit, or default.

**Minor change** — wording, formatting, reordering, typo, whitespace, or a clarifying restatement
that preserves meaning.

**Conservative bias.** When a change is ambiguous — you cannot confidently tell whether it is
material or minor — classify it as **material**. The cost of a wrong "material" is one cheap extra
pass; the cost of a wrong "minor" is shipping an under-hardened artifact. When unsure, material.

## Convergence Condition

Emit `CONVERGED` only when **every** condition holds:

`instability_score = material_changes + open_gaps + pending_questions + unresolved_markers`

is `0` — i.e. zero material changes in your Changes table AND zero entries in Open Gaps — AND
your scope is `full` AND you read every task (or section) AND every executability and spec-coverage
check passes. (The orchestrator separately confirms zero `UNRESOLVED:` markers remain and zero
bubble-up questions are pending; if you see an `UNRESOLVED:` marker in the current artifacts, you
MUST emit `NOT CONVERGED`.)

## Response Format

````
### Verdict: CONVERGED or NOT CONVERGED

### Changes
| # | Artifact | Change summary | Classification: material/minor | Why |

### Open Gaps
- [blocks-execution|inconsistency|cosmetic] [changed|untouched] [gap the judge spotted that this pass missed]   (feeds the next pass; empty if none)

### Reopens
- reopen: <#> | evidence: [file:line or spec quote] | proposed: [the corrected decision]   (empty if none)

### Rationale
[1–3 sentences tying the verdict to the convergence condition, noting any discrepancy with the
Pass agent's self-report]

### Metrics
```json
{"scope": "full", "material_changes": 0, "minor_changes": 0, "regions_changed": [],
 "gaps": {"blocks_execution": 0, "inconsistency": 0, "cosmetic": 0},
 "tasks_read": 0, "tasks_total": 0, "anchors_checked": 0, "anchors_wrong": 0,
 "executable_steps": 0, "run_steps": 0, "spec_items_mapped": 0, "spec_items_total": 0,
 "gaps_in_last_changed_text": 0, "self_report_matches": true, "reopens": 0}
```
````

Metrics fields, all counts from this judgment:

- `scope`: `full` or `scoped`, as your prompt set it.
- `material_changes`, `minor_changes`: rows in your Changes table. `regions_changed`: the
  `artifact:section` of each material change (for example `plan:Task 7`).
- `gaps`: Open Gaps by severity.
- `tasks_read` / `tasks_total`: plan tasks (spec sections when there is no plan) you read in full,
  out of all of them.
- `anchors_checked` / `anchors_wrong`: grounding claims you checked against the source, and how
  many did not match.
- `executable_steps` / `run_steps`, `spec_items_mapped` / `spec_items_total`: the plan checks above;
  `null` when there is no plan.
- `gaps_in_last_changed_text`: open gaps tagged `changed`.
- `reopens`: entries under Reopens (optional; omit only when you were given no log).
- `self_report_matches`: `true` when your diff agrees with the Pass agent's self-report.
