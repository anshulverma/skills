# A TL;DR its author rewrote

Read this before writing a TL;DR. The first version below passed every check in the skill;
its author still rewrote it, and the difference is the lesson.

## The draft

- Trainer jobs sent more traffic than AdFinder's two shadow tiers could serve, and the tiers crashed in three SEVs. The only fix each time was killing jobs, because nothing capped total load and the trainer retried overload errors immediately.
- To fix this, we propose that the trainer back off instead of retrying: each training rank runs its own backoff controller, so overload makes the trainer send less traffic, never more. The scoring service's quota of about 9K requests/s for all callers together becomes the hard cap on total load, which oncall can lower live, and any number of jobs share it without knowing about each other.
- To keep experiments honest while the trainer backs off, failed rows get no fabricated rewards, a sustained loss of scoring stops the job with a checkpoint, and every run reports how much ad-value signal it trained on.
- We ask the GR RL team to agree the trainer design, delivered as the first phase, about 250 lines of trainer changes plus tests (owner: ...), and three asks of the scoring service: typed shed and invalid-request errors with a retry-after hint, a completeness status ..., and the quota landed at about 9K with dry-run off, with setting it to 0 documented as oncall's kill switch.

## The author's version

- Trainer jobs sent more traffic than AdFinder's two shadow tiers could serve, and the tiers crashed in three SEVs. The only fix each time was killing jobs, because nothing capped total load and the trainer retried overload errors immediately.
- To fix this, we propose that the trainer back off instead of retrying: each training rank runs its own backoff controller, so overload makes the trainer send less traffic, never more.
- Additionally, the scoring service's quota of about 9K requests/s for all callers together becomes the hard cap on total load and any number of jobs share it without knowing about each other.
- We ensure integrity of training experiments by not fabricating reward signals and stopping the entire job after a sustained loss of scoring over a period of time. Every training run reports how much ad-value signal it trained on.

## What changed

1. **Scope.** The ask bullet went: the phase size, the owner, the list of asks and the kill switch. So did "which oncall can lower live". The TL;DR is the executive view (problem, fix, guarantee); the body carries sizes, owners, identifiers, asks and operations.
2. **One idea per bullet.** The bullet that carried two mechanisms (per-rank backoff and the server quota) became two, joined by "Additionally".
3. **Intent first.** "To keep experiments honest ..., failed rows get no fabricated rewards" became "We ensure integrity of training experiments by not fabricating reward signals ...": the goal, then the means, in "we ensure X by Y" form.
4. **Everyday words.** "Stopping the entire job after a sustained loss of scoring over a period of time" over a tighter but denser phrasing.
