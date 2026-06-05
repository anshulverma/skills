# 0006. Convergence is measured by an instability score and plotted best-effort

**Status:** Accepted — 2026-06-05

**Context:** The user wants a numeric convergence metric and a chart emitted with the report. The
stop condition is already a conjunction of four zero-checks, so it has a natural scalar form.

**Decision:** Define the per-pass metric as the single canonical formula
`instability_score = material_changes + open_gaps + pending_questions + unresolved_markers`.
It reaches 0 exactly at convergence — the numeric restatement of the stop
condition. Per-pass metrics are stored in `harden.passes[].metrics` and always written to a
`-convergence.csv`. A best-effort `-convergence.png` line chart (instability score plus
components vs. pass number) is rendered via matplotlib, falling back to gnuplot, falling back to
an ASCII sparkline in the report — mirroring the existing `dot -Tpng` best-effort pattern.

**Alternatives rejected:** A separate tunable convergence threshold (convergence is categorical,
nothing meaningful to tune); a "quality score" framed as goodness (the metric measures remaining
instability, which maps cleanly to the stop condition); requiring a renderer (would make the
chart a hard dependency in a pure-Markdown skill).
