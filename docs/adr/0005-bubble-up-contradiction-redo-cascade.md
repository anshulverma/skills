# 0005. A bubble-up answer that contradicts a settled decision triggers the `--redo` cascade

**Status:** Accepted — 2026-06-05

**Context:** During hardening, the user may answer a low-confidence bubble-up question in a way
that directly contradicts a previously settled decision. The loop must reconcile this without
silently holding two conflicting decisions or breaking convergence.

**Decision:** Treat such an answer as a `--redo`-style invalidation, reusing the existing
machinery: mark the contradicted decision `invalidated`, walk `depends_on` to re-queue the
affected gaps, apply the >60%-invalidated "consider re-planning" warning, and continue the
meta-loop under the corrected constraint. Bubble-up handling is otherwise record-and-defer: the
orchestrator asks immediately and the next pass applies the answer.

**Alternatives rejected:** Rejecting the contradicting answer / forcing an explicit `--redo`
(hostile, breaks the "escalate to ask" promise); keeping both decisions and letting a later pass
arbitrate (non-deterministic convergence).
