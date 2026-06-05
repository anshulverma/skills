# 0004. Per-pass snapshots are plain file copies, retained last-2

**Status:** Accepted — 2026-06-05

**Context:** The convergence judge must diff pass-N against pass-(N-1), and an interrupted pass
must be recoverable. Skills are pure Markdown with no VCS coupling, and the target project may or
may not be a git repository.

**Decision:** Before a pass overwrites the artifacts, snapshot the full artifact set as plain
file copies into `docs/auto-plan/reports/snapshots/pass-N/` (preserving original filenames,
including any `adr/NNNN-*.md`). Retain only the last 2 pass directories, pruning older ones as
each pass starts; the per-pass changelog in the state file is the permanent audit trail. The
artifact filename date prefix is frozen at Pass 1's date so paths never churn across multi-day
runs.

**Alternatives rejected:** Git commits per pass (couples to VCS, pollutes project history, fails
in non-repos); a single concatenated history file (breaks per-file diffing); keep-all snapshots
(unbounded disk growth over many passes).
