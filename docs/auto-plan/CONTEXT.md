# CONTEXT.md — auto-plan hardening meta-loop

Glossary and shared definitions for the `--harden` convergence feature. Grillers sharpen
these; the spec uses these terms exactly.

## Glossary

- **Hardening meta-loop**: the outer control loop added by `--harden` that re-runs the entire
  auto-plan flow multiple times until convergence. _Avoid_: "outer loop" (ambiguous), "retry".
- **Pass**: one full re-run of the auto-plan flow over the existing artifacts, executed in a
  fresh isolated context. Numbered from 1. _Avoid_: "iteration" (reserved for the Phase 2
  grill-deepen cycle inside a single pass).
- **Iteration**: a grill-deepen cycle *inside* a single pass (existing `--max-iterations`
  meaning). Distinct from a Pass.
- **Hardening Pass agent**: the sub-agent dispatched by the outer orchestrator to execute one
  Pass with cleared context.
- **Convergence judge**: the sub-agent that compares pass-N artifacts against pass-(N-1) and
  classifies whether the Pass produced a **material change** or only **minor change**.
- **Material change**: a change that adds/removes/alters a decision, scope boundary, interface,
  edge-case handling, or resolves an UNRESOLVED marker. Triggers another Pass.
- **Minor change**: wording, formatting, reordering, or clarification with no change to
  substance. Does not, on its own, justify another Pass.
- **Gap**: something the current artifacts leave unspecified, underspecified, or UNRESOLVED that
  a Pass should fill.
- **Convergence**: the stop state — a Pass yields only minor changes and leaves no open gap.
- **Escalation / bubble-up**: a low-confidence question raised by a (non-interactive) Hardening
  Pass agent, returned to the interactive outer orchestrator, which asks the user.
- **Snapshot**: a copy of an artifact taken before a Pass overwrites it, retained so the
  convergence judge can diff pass-N against pass-(N-1). _Avoid_: "backup", "version".
- **Snapshot-0**: the pre-`--harden` artifact set (the Phase 4 output of pass 1), used as the
  diff baseline so the judge can run after pass 1. _Avoid_: "skip judge on pass 1".
- **Hardening Pass agent**: the single sub-agent executing one Pass — reads the full artifact
  set + decision log in its own cleared context and returns *proposed edits*. It spawns no
  sub-agents of its own. _Avoid_: "re-planner", "sub-orchestrator".
- **Proposed edit**: a structured change the Pass agent returns; the orchestrator (not the
  agent) writes it to disk, after snapshotting. _Avoid_: "auto-edit", "patch applied".
- **Material Change Assessment**: the Pass agent's self-reported yes/no on whether the pass made
  a material change, corroborated by the judge's independent diff.
- **Independent diff**: the judge's own snapshot-vs-current comparison, computed without trusting
  the Pass agent's self-report. _Avoid_: "trust the summary".
- **Conservative bias**: the judge's rule that an ambiguous change is classified as material
  (never minor), trading one cheap extra pass against shipping an under-hardened artifact.
- **Oscillation stop**: orchestrator-owned termination when pass-N's material-change fingerprint
  matches pass-(N-2)'s (ping-pong). _Avoid_: "loop detection".
- **Pass fingerprint**: the set of changed decision/section IDs from a pass's judge verdict; the
  orchestrator compares fingerprints to detect oscillation.
- **Pending question**: a bubbled-up question still awaiting a user answer; the only kind of
  question that blocks Convergence. _Avoid_: treating an answered or deferred question as pending.
- **Deferred (UNRESOLVED)**: a bubble-up question the user skipped, or one suppressed by a low
  confidence threshold / unattended run; recorded with a recommended answer, does not block
  convergence, and is not re-asked.
- **Instability score**: the per-pass convergence metric =
  `material_changes + open_gaps + pending_questions + unresolved_markers`. Reaches 0 exactly at
  Convergence — the numeric restatement of the stop condition. _Avoid_: "quality score" (it
  measures remaining instability, not goodness).
- **Convergence chart**: a best-effort PNG plotting instability score (and its components)
  against pass number, written alongside the planning report. _Avoid_: "graph" (reserve for the
  branch tree).
