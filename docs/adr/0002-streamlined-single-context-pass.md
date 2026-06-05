# 0002. Hardening Pass is a single-context review-and-patch, not a nested re-plan

**Status:** Accepted — 2026-06-05

**Context:** A `--harden` pass could either re-invoke the full `auto-plan` skill (spawning its own
Grillers/Writers/Reviewers — deep agent nesting) or do a single-context review-and-patch of the
existing artifacts. Nesting compounds cost and failure probability and risks harness nesting
limits; the user's intent is "fresh eyes on the same artifacts," which is review-and-patch.

**Decision:** Each pass is one fresh sub-agent that reads the full artifact set in its own
context, proposes **material-only** edits as full-file replacement bodies, and spawns no
sub-agents of its own. It returns proposed edits; the orchestrator applies them after
snapshotting. Holding all artifacts in one context is also what lets a pass catch cross-artifact
inconsistencies the original per-branch Grillers structurally cannot see.

**Alternatives rejected:** Full skill re-invocation per pass (deep nesting, regenerates rather
than hardens, prose churn); the pass agent writing files directly (races the snapshot, gives a
fresh isolated agent ownership of target-file and state I/O).
