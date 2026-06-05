# 0003. The convergence judge diffs independently and is biased toward "material"

**Status:** Accepted — 2026-06-05

**Context:** A hardening pass could under-report its own changes, and a judge that mis-rates a
small material change as minor would stop the loop early (false convergence), shipping an
under-hardened artifact. The user weights robustness over speed.

**Decision:** The convergence judge runs after every pass and **independently diffs** the
snapshot against the current artifacts; the Pass agent's self-reported assessment is only a
cross-check. When a change's classification is ambiguous, the judge applies a **conservative
bias** and classifies it as material, forcing one more pass. Convergence requires zero material
changes, zero open gaps, zero UNRESOLVED markers, and zero pending bubble-up questions.

**Alternatives rejected:** Trusting the pass agent's self-reported change summary (cheaper but
vulnerable to under-reporting); neutral/best-guess classification of ambiguous changes (fewer
passes but risks false convergence). The cost of a false-material is one cheap extra pass; the
cost of a false-minor is an under-hardened deliverable.
