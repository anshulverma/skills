# Hardening Pass Protocol

This is your playbook for one hardening **pass**. Follow it exactly. Respond using
`HARDENING-PASS-RESPONSE-TEMPLATE.md` (its headers are a contract with the orchestrator).

## Your Job

Harden the **entire** artifact set — spec, ADRs, plan, CONTEXT.md — in this one cleared context.
You are doing a **review-and-patch**, not a re-plan. You hold all artifacts at once, so your
unique value is catching cross-artifact gaps and inconsistencies that the original per-branch
grilling could not see. Read every artifact and the decision log included in your prompt, find
what is unspecified / underspecified / inconsistent / weakly-hardened, and propose edits that fix
it. You drive the artifacts toward passing the review checklists included in your prompt
(`SPEC-REVIEW-CHECKLIST.md`, `PLAN-REVIEW-CHECKLIST.md`, `FINAL-REVIEW-CHECKLIST.md`).

## The Material-Only Rule

Propose an edit **only if it is a Material change** — one that:

- adds, removes, or alters a decision;
- changes scope (adds or drops a requirement or task);
- changes an interface, type, signature, or schema;
- adds, removes, or alters an edge case or its handling;
- resolves or introduces an `UNRESOLVED:` marker;
- adds, removes, or alters an ADR or its decision;
- changes a numeric threshold, limit, or default.

**Standalone minor edits are FORBIDDEN.** Do not propose wording, formatting, reordering, or
typo-only changes on their own. A minor tweak may ride along only inside a section you are already
editing for a material reason. This rule is what guarantees the loop converges: if there is nothing
material left to change, you return zero edits and the loop stops.

## Edit Format

For every artifact you touch, return its **full replacement body** under `### Edits` — not a diff.
The orchestrator snapshots the prior version before applying and computes its own diff. Never write
to disk yourself; you only propose. The orchestrator owns the ordering snapshot → apply → state →
judge.

## Confidence Gating

For each gap you find:

- If you can resolve it **at or above** the run's `--confidence-threshold` (a direct match in the
  user model brief, an ADR, the decision log, or the codebase context) → make the edit and record
  the source under `### Gaps Filled`.
- If you **cannot** (genuinely novel trade-off, conflicting signals, below threshold) → do NOT
  guess. Record a `### Bubble-Up Questions` entry with your recommended answer, and leave the gap
  in place (optionally keeping an `UNRESOLVED:` marker so it stays visible).

## What NOT To Do

- **Do not re-invoke auto-plan** and **do not spawn sub-agents** of your own — you are a single
  self-contained pass.
- **Do not explore the codebase yourself.** If you need a file you were not given, list it under
  `### Bubble-Up Questions` as `Files Needed: [path/query]`; the orchestrator fetches it and
  re-dispatches this pass.
- **Do not edit against a settled decision.** Settled decisions in your prompt are facts. If you
  believe one is wrong, record it under `### Bubble-Up Questions` flagged
  `conflict-with-settled: dNNN` with your reasoning — never silently contradict it in an edit.
- **Do not churn prose.** No cosmetic-only edits — propose only material edits (see the
  Material-Only Rule above).
