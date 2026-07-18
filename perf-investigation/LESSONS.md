# Lessons (the feedback loop)

Append a lesson whenever an investigation teaches you a reusable technique, gotcha, or cheap-repro trick. Keep each entry: **Lesson / Why / How to apply.** Newest at top. These are seeded from the MRS/SIA multimodal SFT GPU-utilization investigation.

## Verify instrumentation actually emitted before trusting a null result
- **Why:** In a GPU run, an opt-in `print()`-based timing hook (`GRAIN_SAMPLE_TIMING`) produced **0 lines** even though the env flag was set, so "no signal" was ambiguous between "the fix did nothing" and "the code path never ran / the log wasn't captured."
- **How to apply:** Every instrumentation arm must emit a proof-of-life line first (e.g. `[PHASE_X] enabled window=16`). If you see zero instrumentation output, treat the run as **invalid**, not as evidence. Grain workers are subprocesses: use `print(..., flush=True)` (not `logging`) and confirm the capture stream (stdout vs stderr) actually contains it.

## A dataloader metric is not the bottleneck until it moves step_time
- **Why:** `timing/get_microbatch_s` swung 3x (6.68 → 2.17 → 3.19s) across cache/prewarm/baseline runs while `trainer/step_time` and `tflops` stayed flat. The grain prefetch buffer + background worker processes hide average dataloader latency behind compute, so optimizing it changed nothing.
- **How to apply:** Before spending effort on a dataloader/input-pipeline fix, prove the stage is on the critical path: change it and check `step_time`/`tflops`, not just the stage's own metric. If the stage metric moves and step time doesn't, the stage is already hidden — stop optimizing it.

## Read what a metric measures before trusting it
- **Why:** `trainer/batch_time_proportion` stayed ~87% regardless of dataloader speed. It is "step time that isn't compute," not "time waiting for the dataloader" — so it did not implicate the stage we assumed.
- **How to apply:** In Phase 1 baseline, for every metric you'll rely on, read the code that emits it and write down its exact definition. Especially distinguish dataloader-pull time from in-forward costs (e.g. `hydrate()`), which land in step time, not the dataloader metric.

## Averages hide tails; the tail is often the real killer
- **Why:** `get_microbatch_s` avg was 2-7s but **max 100-160s**; `step_time` max was 230-270s. The original starvation root cause was occasional stalled fetches with no timeout/retry that drain the prefetch buffer — invisible in the average.
- **How to apply:** Always pull avg AND max (and p90/p99 if available), and chart the time series. A fix that lowers the average but not the tail hasn't fixed a tail-driven problem.

## Test the dataloader / CPU-side pipeline locally to skip MAST scheduling latency
- **Why:** A local run of the dataloader on a 96-CPU devserver via `rl/run.sh` iterated in ~90s vs ~2h for a MAST GPU job, and still reproduced the per-image fetch behavior (local 807 ms/img matched the GPU worker's 864 ms/img). It also caught two real bugs cheaply.
- **How to apply:** For input-pipeline / CPU-side / decode / fetch questions, build a local repro first (`cd genai/mrs_research/deps/msl && rl/run.sh python <probe>.py`). Reserve MAST GPU runs for questions that genuinely need the GPU/model (forward/backward/comms). Confirm the local tier is representative by matching one shared metric against a real run.

## MAST launch hygiene
- **Why:** Cold full builds stall when launching from a modified stack that isn't rebased onto the latest warm; parallel launches contend.
- **How to apply:** Rebase onto latest warm before launching from a modified working copy; launch jobs one at a time, not in parallel. Name every job with the investigation ID so the whole run set is greppable.

## autodeps (arc lint -a) can over-prune unrelated BUCK targets
- **Why:** Running `arc lint -a` on a couple of changed files rewrote whole BUCK files, stripping deps from unrelated targets and adding a duplicate macro load — which would have broken the build for many targets.
- **How to apply:** After `arc lint -a`, diff the BUCK files. If it touched targets you didn't change, revert and hand-apply only the minimal deps your new imports need, then `buck2 build` the specific targets to verify.
