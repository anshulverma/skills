# 0001. `--harden` is an opt-in outer meta-loop, not a default

**Status:** Accepted — 2026-06-05

**Context:** Hardening re-runs the whole flow multiple times, multiplying cost. Making it the
default would change every existing `auto-plan` invocation and surprise users with multi-pass
runs.

**Decision:** Add hardening as an opt-in bare flag `--harden` with a separate `--max-passes`
budget (default 3). Pass 1 is the normal interactive run; Passes 2+ run via fresh sub-agents in a
new Phase 5 wrapper. "Pass" (outer) and "iteration" (inner, `--max-iterations`) stay distinct
vocabulary and distinct budgets.

**Alternatives rejected:** Default-on hardening (changes existing behavior, unbounded cost);
overloading `--max-iterations` to also bound passes (conflates two loops, makes cost reasoning
ambiguous); making `--harden` take a numeric value (breaks the bare-flag convention).
