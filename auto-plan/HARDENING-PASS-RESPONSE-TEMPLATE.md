# Hardening Pass Response Template

Structure your response with these exact headers. The orchestrator's Phase 5 collection logic
reads these sections to collect your results. Missing sections are treated as empty. Do not rename,
reorder, or add headers — the header set is a contract with the orchestrator.

---

### Edits

One entry per artifact you are changing. Return the **full replacement body** of the file — not a
diff. The orchestrator snapshots the prior version before applying, so it computes its own diff.

- [artifact: spec|adr-NNNN|plan|context] | [section/anchor] | [full replacement body] | Why: [reason]

### Decisions Changed

- [d-id or NEW] | [question] | [old answer → new answer] | Confidence: high/medium/low | Source: [memory/ADR/codebase/principle/best-judgment]

### Gaps Filled

- [gap] | [how filled] | Source: [...]

### Unresolved Resolved

For each `UNRESOLVED:` marker you removed by resolving it:

- [original UNRESOLVED question] | Resolution: [...] | Confidence: high/medium/low

### ADR Candidates

Only if ALL THREE are true: hard to reverse + surprising without context + result of a real trade-off.

- Title: [..] | Context: [1 sentence] | Decision: [..] | Alternatives: [what was rejected and why]

### Bubble-Up Questions

Low-confidence questions you could not resolve at or above the run's confidence threshold. The
orchestrator returns these to the user. May carry a `conflict-with-settled: dNNN` flag (you found a
settled decision you believe is wrong — never edit against it) or a `Files Needed: [path/query]`
note (you need a file you were not given).

- [question] | Recommended: [your best answer] | Confidence: low | Why uncertain: [what's missing]

### Material Change Assessment

- material_change: yes|no | Summary: [one line: what this pass changed] | Remaining gaps: [...]
