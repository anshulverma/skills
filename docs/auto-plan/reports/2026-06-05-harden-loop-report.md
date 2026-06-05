# Planning Report: auto-plan Hardening Meta-Loop (`--harden`)

## Execution Stats
- Mode: default (single planning run — this run designed `--harden`; it did not use it)
- Sub-agents spawned: 6 (5 Grillers, 0 Writers [orchestrator-authored], 1 Reviewer, 0 Researchers)
- Grilling iterations: 1 (all 5 uncertain branches resolved in one parallel round)
- Questions auto-answered: 31
- Questions asked to user: 5 (1 clarification round of 4 + 1 free-form clarification)
- Branches explored: 7 (1 discovered mid-run from a user message)
- Max depth reached: 1
- Conflicts detected: 3 (max-passes default 3-vs-5; flag name; snapshot-retention vs oscillation) — all reconciled
- Review gate: 1 Reviewer, 3 checklists; FAIL→fix→PASS (4 issues fixed)

## Decision Log
| # | Question | Answer | Conf | Source | Branch |
|---|----------|--------|------|--------|--------|
| d001 | Opt-in vs default | Opt-in bare flag `--harden` | med | principle | b001 |
| d002 | Context-clearing mechanism | Thin orchestrator loop; fresh sub-agent per pass | high | user | b002 |
| d003 | Stop criterion | Convergence judge: material vs minor | high | user | b003 |
| d004 | Re-feed scope | Full artifact set each pass | high | user | b002 |
| d005 | Interactivity | Bubble up to interactive orchestrator | high | user | b005 |
| d006 | Purpose of passes | Fill gaps + harden; meaningful = material | high | user | b003 |
| d007 | Output strategy | Overwrite in place + per-pass snapshots | med | principle | b004 |
| d008 | Pass budget | `--max-passes` default 3 (≠ `--max-iterations`) | med | principle | b001 |
| d009 | Loop placement | Phase 5 wrapper; pass 1 interactive, 2+ via agent | high | principle | b001 |
| d010 | Flag composition | legal set; `--dry-run` error; `--redo` independent | med | principle | b001 |
| d011 | Input modes | topic string + spec file | high | codebase | b001 |
| d012 | Pass agent nesting | Single-context review-and-patch; no sub-agents; opus | high | principle | b002 |
| d013 | Write vs propose | Propose; orchestrator applies after snapshot | high | principle | b002 |
| d014 | New fragments | 3 fragments | high | principle | b002 |
| d015 | Pass response headers | 7 headers (contract) | high | principle | b002 |
| d016 | Cosmetic churn | Material-only edits → convergence | high | principle | b002 |
| d017 | Judge trust | Independent diff; summary cross-check only | high | principle | b003 |
| d018 | Material/minor rubric | Rubric + conservative bias (ambiguous→material) | high | principle | b003 |
| d019 | Judge cadence/baseline | Every pass; Snapshot-0; opus | high | principle | b003 |
| d020 | Stop condition | 0 material + 0 gaps + 0 UNRESOLVED + 0 pending | high | principle | b003 |
| d021 | Termination conditions | converged/max_passes/oscillation/failed | high | principle | b001 |
| d022 | Oscillation | Orchestrator-owned; fingerprint N vs N-2 | med | principle | b001 |
| d023 | Pass failure | Retry once; no budget consume; abort after 2 | med | codebase | b001 |
| d024 | State schema | `harden` object; two-phase write; full rewrite | high | codebase | b004 |
| d025 | Snapshots | File copies; last-2 retention; frozen date | high | principle | b004 |
| d026 | `--resume` | Via convergence_status + current_pass | high | codebase | b004 |
| d027 | `--redo` | Independent; no auto-re-harden; no snapshots | high | codebase | b004 |
| d028 | Escalation handling | Record-and-defer; next pass applies | high | principle | b005 |
| d029 | Confidence gating | low/medium/high/paranoid table | high | codebase | b005 |
| d030 | Unattended mode | `--unattended` + auto-detect → UNRESOLVED | med | principle | b005 |
| d031 | Bubble-up dedup | Dedup; only pending blocks convergence | high | principle | b005 |
| d032 | Contradiction | Reuse `--redo` cascade | med | codebase | b005 |
| d033 | `--auto-commit` granularity | Once per pass | med | best-judgment | b001 |
| d034 | Convergence metric | `instability_score`; CSV always | high | user | b007 |
| d035 | Convergence chart | Best-effort PNG; matplotlib→gnuplot→ASCII | high | user | b007 |
| d036 | Documentation surface | SKILL/CLAUDE/README + 3 fragments | high | principle | b006 |

## Branch Tree

```
Hardening meta-loop (7 branches, 36 decisions)
├── b001 Outer-loop control flow + termination (10) [auto-answered]
├── b002 Hardening Pass agent contract (6)          [auto-answered, user mechanism]
├── b003 Convergence judge + change detection (5)   [auto-answered, user criterion]
├── b004 State schema + snapshots (4)               [auto-answered]
├── b005 Escalation / bubble-up (5)                 [auto-answered, user interactivity]
├── b006 Documentation surface (1)                  [from existing conventions]
└── b007 Convergence metric + chart PNG (2)         [discovered mid-run — user request]
```

(See `2026-06-05-harden-loop-tree.dot` / `.png` for the graphviz version.)

## Review Findings (fixed before completion)
1. `convergence_status` enum listed unused `escalated` but omitted the `failed` it actually sets → enum corrected to `…oscillation | failed | interrupted`; `--resume` terminal set updated.
2. State example `judge_verdict: "material"` used the wrong vocabulary → changed to `"NOT CONVERGED"` (material/minor lives in `metrics`).
3. `instability_score` formula was line-wrapped in ADR 0006, breaking the cross-file identity check → reflowed to one canonical line, now byte-identical in spec + ADR 0006 + plan grep targets.
4. Plan Task 8 identity assertion strengthened by (3).

## Preference Updates
- Saved `preference-escalate-when-low-confidence` (feedback; agent-orchestration, skill-design)
- Saved `preference-convention-consistency` (feedback; skill-design, agent-orchestration)

## Artifacts Produced
- `docs/auto-plan/CONTEXT.md` (glossary)
- `docs/auto-plan/specs/2026-06-05-harden-loop-design.md` (design spec)
- `docs/adr/0001`–`0006` (six ADRs)
- `docs/auto-plan/plans/2026-06-05-harden-loop.md` (implementation plan, 8 tasks)
- `docs/auto-plan/reports/2026-06-05-harden-loop-state.json` (state)
- `docs/auto-plan/reports/2026-06-05-harden-loop-tree.dot` / `.png` (branch tree)
- `docs/auto-plan/reports/2026-06-05-harden-loop-report.md` (this report)
