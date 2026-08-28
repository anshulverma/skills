---
name: diff-authoring
description: How to write a Phabricator diff so a reviewer can actually review it: a clear title (no task IDs), a concise hierarchical self-contained summary that leads with the goal and hyperlinks external concepts, and a diff-specific test plan with real evidence. Also keeps planning cruft (task IDs, ADRs, spike labels, spec paths, dates) and AI-tells (em-dashes) out of titles, summaries, test plans, and code comments. Use whenever creating or updating a diff (jf submit / meta phabricator.diff update). After publishing, pair with the clearing-diff-signals skill to drive CI signals, automated AI reviews (Devmate / Mitra), and governance/RADAR rules (suppression eligibility, CodeHub coverage) to green. Complements stack-review (the review loop) and creating-or-updating-diffs (mechanics).
---

# diff-authoring

Write each diff so a reviewer who has never seen the project can review it from the title, summary, and test plan alone. Apply this to every diff you create or update.

## Title

Start every title with the bracketed tag or tags the surrounding area already uses, then a short specific description.

**Derive the tags from the area. Never carry a tag in from anywhere else.** Every tag in this document is a placeholder: `[myproject]`, `[myfeature]`. A tag copied out of this document, out of another project, or out of a different stack is always wrong, and it is wrong silently, because the title still looks well-formed. Look up what the area actually does before writing a title:

```
sl log <directory-you-are-touching> -T "{desc|firstline}\n" -l 20 \
   --reason "read the local diff-title convention - sl help log"
```

Read what comes back and match it. Conventions differ legitimately by area: some use a single project tag (`[myproject] thing.py: what it does`), some a project tag plus the feature the stack builds (`[myproject][myfeature] thing.py: what it does`). Both are right where they are used. How many tags to use is the area's call, never this document's.

- **If your stack sits on top of someone else's commits, match their titles.** The base commits are the most authoritative sample available, and a stack whose tag changes halfway reads as two unrelated workstreams.
- The tag is NOT the edited file name.
- If the area shows no consistent convention, propose two or three options and ask the user. Do not guess.
- After the tags, a short specific description, matching the area's style.
- Do NOT put a task ID in the title. Tasks are linked via the Tasks field (below).
- Do NOT use em-dashes (`—`). Use a colon or plain words: `[myproject] masking.py: forward corruption`, not `[myproject] masking.py — forward corruption`.

## Tasks

- Link the task via the Tasks field, not the title or summary text:
  `meta phabricator.diff update -n D<n> --add-tasks=T<n>`
- A task ID never appears as a provenance stamp in the title, summary, or code.

## Reviewers

- Set reviewers via the Reviewers field (a `Reviewers:` commit-message trailer, or `--add-reviewers` on `jf template` / `meta phabricator.diff update`), never in the title or summary.
- **For a project / group reviewer, ALWAYS use the `#`-prefixed project tag**, quoted so the shell does not treat `#` as a comment: `--add-reviewers "#myproject"`. A bare name (`--add-reviewers myproject`) resolves to BOTH the `#myproject` project AND a `myproject` **unixname user**, silently attaching the wrong real account as a reviewer across the whole stack. If the user says "add the X project/team/group as reviewer", that means `#X`, not `X`.
- `#myproject` here is a placeholder, exactly as in Title above. Use the project the code you are touching belongs to, never one carried in from this document or another stack.
- Fix a wrongly-attached unixname after the fact, per diff: `meta phabricator.diff update -n D<n> --remove-reviewers <unixname> --add-reviewers "#project"`, then `jf sync -s` so the corrected Reviewers field is pulled back into the local commit messages (otherwise a later `jf submit` re-adds the bad reviewer from the stale local message).

## Summary

Lead with the goal, then add only the sections that matter for this diff. Keep it tight (roughly 5 to 10 lines). Bullets over paragraphs.

**The test plan is NOT part of the summary.** It is a separate Phabricator field. Never put a `## Test Plan` (or `Test Plan:`) heading inside the summary body; the summary describes the change, the Test Plan field describes how you verified it (see the Test plan section below).

Use a clear visual hierarchy with Remarkup headings (`##` for sections, `###` for sub-points when a section needs them); bullets under each heading.

1. **Goal** (always, first): a `## Goal` section, 1 to 2 plain lines saying what the diff does and why.
2. Then only the sections that matter. **Choose them to fit what the diff actually is, rather than filling in a fixed template.** The headings are a vocabulary, not a form; a section you have nothing real to put under is noise, and a section the diff needs but the template lacks should be invented.

**State the current state before explaining it.** `## Goal` says what the diff is for, in a line or two. It is not the place to also carry the symptom. Immediately after it, before any root cause or background, give the reader the situation as it stands today: what is broken, what is missing, what today's behavior is. A reviewer cannot judge a cause or a fix without first knowing what is wrong.

Name that section for what it actually holds - `## What is broken`, `## What is missing`, `## Today` - and make it concrete: the observable symptom, who or what it affects, and what it currently costs. "The pipeline does not work" is not a symptom; "the release stalls in the test node and the package is never tagged, so every launch still pays a 20 minute build" is.

**Match the shape to the kind of diff.** The most common mistake is describing a bug fix as though it were a feature: `## Background` then `## What it changes` buries the one thing a reviewer needs, which is *why it broke*. Fixes get their own shape:

| Kind of diff | Shape that fits |
|---|---|
| **Fixes a bug** | `## Goal`, `## What is broken`, `## Root cause`, `## Fix`, plus `## Risk` if the fix has a blast radius. Root cause states the defect and the mechanism by which it produced the symptom; Fix states what now happens instead. |
| **Adds a capability** | `## Goal`, `## What is missing` (the gap today, and its cost), `## Background` (only if a domain concept is load-bearing), `## What it adds`, `## Risk` |
| **Changes existing behavior** | `## Goal`, `## Today` (the behavior being replaced), `## What it changes`, `## Why` (when the choice is non-obvious), `## Risk` |
| **Removes something** | `## Goal`, `## Why it is unused`, `## What it removes` |
| **Pure refactor** | `## Goal`, `## Today` (only when the current shape is the point), `## What it changes`, and a line stating behavior is unchanged |

Skip the current-state section only when the title and goal already make it obvious and a sentence would add nothing. That is rarer than it feels: the author knows what is wrong and forgets the reviewer does not.

For a fix, `## Root cause` earns its place only if it says something the symptom does not: the specific defect, and the causal step from defect to symptom. "The sampler was misconfigured" is not a root cause; "the sampler sharded over the global world group, so ranks inside a TP group each got a different slice, and MoE routing then diverged per rank" is.

Diffs that genuinely do two things (a capability plus a correctness fix that surfaced while building it) can carry both `## What it adds` and `## Root cause` / `## Fix`. If that reads awkwardly, it is usually a sign the diff should be split.

`## Background` comes first when present, right after `## Goal`, so the reader has the context before the change. Add `###` subheadings only when a section genuinely has sub-parts.

**The test plan follows the same principle:** its structure should reflect what was actually verified, not a fixed order. A fix's test plan leads with the regression evidence (the thing that used to fail and now does not); a capability's leads with the exercise of the new path; a refactor's leads with the equivalence check. Do not pad it with sections that verify nothing.

Rules:
- **Say what it IS in plain English, AND keep it scannable.** Three failure modes to avoid: (1) a symbol inventory (listing the classes/functions/dataclasses it adds), (2) a wall of text (long unbroken paragraphs), and (3) naming specific reader-unknown identifiers only to make a category point (e.g. listing the exact variables a call does or does not touch, when the reviewable fact is what *kind* of thing they are). A reviewer skims dozens of diffs a day. Target: a 1-2 line `## Goal` plus a few short bullets, each a single tight plain-English point (about one line). Explain the concept in words, not a table of contents of the file; name a specific type only when it carries meaning, then say what it is in a few words. Never a multi-line paragraph; tighten any bullet that runs past ~1.5 lines or names 3+ identifiers.
  - Good (plain English, scannable):
    ```
    ## Goal
    The demo's data model: a Gradio-free description of a demo so the rest of the system can build and test it without a GPU or a running UI.
    ## What it does
    - Describes a demo as data: the inputs to show, how to run the model, and how to render the result.
    - Imports no Gradio or model library, so a demo's shape stays a cheap, testable value.
    - Reserves an optional streaming path for progressive output.
    ```
  - Bad - symbol inventory: "adds `InputComponent`, `RenderPayload`, `DemoSpec`, `SessionMetadata`."
  - Bad - wall of text: the same content as one long paragraph with no bullets.
- **Describe changes by behavior and intent, not as a per-edit changelog.** The change sections (`## What it changes` / `## What it adds` / `## What it removes`) are a few high-level points a reviewer skims to grasp the *shape* of the change, NOT a line-by-line log of every code edit. Do NOT enumerate low-level specifics that belong in the code and read as if transcribed from the diff hunks: exact exception types and their trigger conditions, the precise math/formula of a computation, per-function control flow, or which internal helper does what. State what each change *accomplishes* and *why it matters*; if one specific mechanism is a genuine review risk, give it a single short line under `## Risk`, not a mechanics dump in the change list. Smell test: if a bullet names an exception, a formula, or a branch condition, lift it up to the behavior it produces or cut it.
  - Bad - changelog / mechanics dump: "`shard_hf_model` wraps with `fsdp_mesh`; HSDP + expert parallelism raises `MitraValueError`. `mesh_aware_clip_grad_norm_` reduces dense grads over the shard axis only: the flattened mesh would inflate the norm by `sqrt(dp_replicate)`, causing over-clipping. `auto_shard_dim` keys off the shard sub-axis."
  - Good - behavior and intent: "Wraps HuggingFace models with the 2-D mesh so they shard within a host and replicate across hosts instead of full-sharding. Makes gradient-norm clipping HSDP-correct, so a replicated run clips identically to a fully sharded one."
- **When you name symbols only to contrast their category or type, name the category, not the individual identifiers.** If several identifiers appear purely to illustrate "what kind of object" something is, the reader has never seen those names and they read as noise, especially when they are introduced with no prior description. State the distinguishing category instead.
  - Bad - esoteric identifiers to make a category point: "`threshold` is a plain attribute, not a registered metric state, so `Metric.to(device)` moves `num_tp`/`num_fp`/`num_fn` but leaves `threshold` on its original device." (the reader has no idea what those three are, or why they matter)
  - Good - name the category, not the names: "`threshold` is a plain attribute, not a registered metric state, so `Metric.to(device)` moves the registered states but leaves `threshold` behind on its original device."
- **On-topic only: every line must explain the diff's own contents.** The summary describes what THIS diff contains and does - nothing else. Cut meta-commentary that does not describe the code: how the change was split or carved out, its position in a stack, "so it can be reviewed on its own", "split out from D123 / the handler", "part 2 of 3", "as a follow-up to", or simply noting that a sibling diff exists. Cross-diff ordering lives in Phabricator's stack/dependency graph, not in prose. Before keeping any sentence, ask "does this help a reviewer understand what this diff changes?" - if not, delete it. (A `## Out of scope` line is justified only when it stops a reviewer from expecting behavior that is genuinely absent, never to narrate the split.)
  - Bad - off-topic meta: "Split out from the handler (D112422943) so it can be reviewed on its own." / "This is the first of two diffs; the config lives in the follow-up."
  - Good - on-topic: "`AccumulatingScatterView` accumulates embeddings across submits and renders them as a 2D/3D scatter plot via `reduce.project_embeddings` + plotly."
- **Give background before the change when a domain concept is load-bearing.** If understanding the diff requires knowing what some external model, algorithm, math, or technique IS (e.g. `WaveMix`, a `wavelet` / DWT, `LoRA`, `RoPE`, a specific loss or sampler), do not assume the reviewer knows it. Add a short `## Background` section right after `## Goal`, before the change is described, that says in a few plain-English bullets what the concept is, why this code uses it, and what today's behavior is. Keep it tight (a few one-line bullets, not a tutorial) and hyperlink the concept's first mention to its paper/docs per the clickable-link rule. Rule of thumb: if a competent reviewer from another team would have to go look up a term to review the diff, that term earns a Background line. A one-off familiar term can instead be explained inline in parentheses; reserve the section for when the diff genuinely rests on the concept.
- **Never defend a decision to the reviewer.** This is the most common slop in an AI-written summary, and it is the same rule the code-comment section below already states, applied one level up: the summary is for the engineer reading this change, not for winning an argument with today's reviewer. It says what the code does. It does not pre-empt an objection nobody raised, justify a rejected alternative, or explain why a test is shaped the way it is. Those belong on the review thread, where the person who raised the point can reply.
  - Bad: "Carrying both would put back the dead-knob shape where `level` no longer determines behaviour." (defends a rejected alternative)
  - Bad: "so deleting the code that fills it fails a test instead of coincidentally producing the right number" (justifies a test-design choice)
  - Bad: "What it buys is one fewer named state. It does not make bad states unrepresentable in general." (argues with an imagined objection)
  - Good: "The inactive level's clamp is dropped, as `grpo_token_clip_epsilon` already is at sequence level."

  Mechanical tells: a clause containing **"rather than"**, **"instead of"**, **"would have"**, **"does not mean"**, **"what this buys"**, **"the same trade"**; a sentence whose subject is the reader, the reviewer or the alternative design; a sentence that only makes sense as a reply.

  A tell is a prompt to look, not an automatic cut. Contrasting two things the *code* does is fine ("the gate maps to presence, not to a field"); contrasting your choice with one you rejected is not. Ask which of the two it is. Either way the sentence usually reads better once the contrast is dropped and the fact stated straight, so rewrite first and only keep the contrast if it carries information the positive form loses.
- **A sentence that would be equally true of any diff carries no information.** "A mistake here becomes a mistake once this runs", "this is important to get right", "correctness matters here" apply to all code and single out nothing. The shape to watch for: one of these appearing immediately after a reassuring fact, to claw back urgency the fact just removed. That is the defending-a-decision reflex in future tense. Delete it and let the reassuring fact stand on its own.
- **Count before you ship.** At most ~10 bullets across the whole summary, each at most one line. A bullet that wraps is carrying two facts or an argument: split it or cut it. A section with nothing real under it gets deleted, not filled.
- **Reviewer-oriented**: enough to review, not verbose, not in the weeds.
- **Self-contained**: the reader either understands fully from the summary, or follows a clickable reference. No bare internal jargon or project labels (e.g. `C3`, `Gate-2`, `P3`, `Spike-2`) unless you explain it in plain words right there.
- **Every reference must be a clickable link.** Never leave a bare non-clickable token (a `manifold://` path, a job name, a raw identifier) sitting in the text as if a reader could follow it. Make it a link:
  - External model / dataset / algorithm / technique: hyperlink the first mention to its paper or blog, e.g. `[LLaDA](https://arxiv.org/abs/2502.09992)`, `[GSM8K](https://arxiv.org/abs/2110.14168)`, `[MMLU](https://arxiv.org/abs/2009.03300)`, `[LoRA](https://arxiv.org/abs/2106.09685)`, `[RoPE](https://arxiv.org/abs/2104.09864)`.
  - Task / diff: `T123` / `D123` (Phabricator auto-links these).
  - MAST job or training run: link the session, e.g. `[session](https://www.internalfb.com/mitra/sessions/<id>)`, and link the job name itself, e.g. `[torchx-...](https://www.internalfb.com/mitra/sessions/<id>)`. Do not paste the job name as plain text.
  - A `manifold://bucket/path` artifact: it is NOT clickable as written. Link it via the explorer URL: `[hf_epoch_4_train_step_1000](https://www.internalfb.com/manifold/explorer/<bucket>/<path>)`.
  - Wikis, docs, Workplace posts: link the URL.
- **No planning cruft**: no ADR references, no "part of master T...", no task IDs as stamps, no spec/doc file paths, no "researched <date>", no Spike-N labels.
- **Sound human, not AI-generated**: no em-dashes (`—`); use `:`, `,`, `(...)`, or ` - `. Do not over-bold, do not over-structure, vary phrasing. Backtick code symbols. Do not hard-wrap. Do not escape backticks.

### Call out production exposure, and name the QRT

**If the diff touches anything a QRT or other production experiment depends on, say so.** A reviewer triaging a queue decides how hard to look based on blast radius, and "this touches the QRT" is the fact that changes that decision. Leaving them to infer it from a flow ID is withholding the thing they needed first.

**Do not give it its own section.** It splits across the two sections that already exist, and putting it in a third breaks the reading order and duplicates a fact:

| What | Where | Why there |
|---|---|---|
| **Which** experiment, linked, and **what of it the diff touches** | a bullet in the current-state section (`## What is missing` / `## Today`) | the exposure IS part of what is wrong today, and the reader meets it while learning the problem rather than before it |
| **Whether it is reachable today** | first bullet of `## Risk` | that is a blast-radius question, and `## Risk` is where a reviewer already looks for one |

The order matters more than the emphasis. A `## QRT exposure` section between `## Goal` and the current-state section reads as though the reviewer already knows what is broken, because it has to describe the exposure in terms of a problem they have not been told about yet. Bold the lead clause instead: **"These are QRT recipe fields."** carries the same triage weight in the right place.

Say it even when the answer is reassuring. "Nothing imports this package yet, so no running job is affected" is worth a Risk bullet, because otherwise the reviewer establishes it themselves and pays for your silence. State the exposure once: if the current-state bullet and the Risk bullet are saying the same thing, the fact belongs in one of them, not both.

**Check, do not assume.** Get the experiment's real config with `meta ai.workflow-run inputs --id <flow>` and compare it against what the diff touches. A committed YAML is not the recipe. Confirm the run is actually current before calling it live: a `SUCCEEDED` run from three weeks ago is production evidence, not a running job, and the two words are not interchangeable.

## Test plan

The test plan is a **separate Phabricator field**, never a section inside the summary. In a commit message, put it under a `Test Plan:` trailer at the end (jf/arc parse that line into the dedicated field, the same way `Reviewers:` and `Differential Revision:` are parsed); via the CLI, set it with `meta phabricator.diff update -n D<n> --test-plan="..."`. Keep the `Summary:` body and the `Test Plan:` field distinct.

Make it specific to THIS diff (not a copy of the stack's overall plan). Pick the category that fits:

1. **Docs / config only, no runnable behavior**: keep it to one short line stating there is nothing to build or run (e.g. `Docs only, no code to build or run.`). Do NOT narrate a manual review or re-list what the summary already covers, that is redundant.
2. **Unit tests**: the exact `buck2 test //target` command plus the captured result (e.g. `Pass 10`).
3. **Build / typecheck only** (pure refactor, no behavior change): the `buck2 build` or `[typecheck]` result, leading with why that is sufficient.
4. **Runs a job** (training / eval / pipeline): run it locally or on MAST and report it concisely with the job and artifacts as clickable links plus the final train/eval metrics. Keep it to a sentence or two, not a log dump. Template:

   > Job (MAST): <one line of what ran>. [session](https://www.internalfb.com/mitra/sessions/<id>) (job [<jobname>](https://www.internalfb.com/mitra/sessions/<id>), state COMPLETE / exit 0), <key facts: steps, epochs, parallelism>. Checkpoint at [<short label>](https://www.internalfb.com/manifold/explorer/<bucket>/<path>). Metrics: <e.g. GSM8K 0.6611, MMLU 0.6520>.

   Both the session and the job name link to the session URL; the checkpoint links to the Manifold explorer URL (never a bare `manifold://` path).

**Be brief, do not enumerate every case.** State what is covered at a high level and stop; a reviewer reads the tests for the specifics. Write `Covers tier-name determinism and protocol scoping, and all branches.`, NOT `... all branches: absent launches once, READY reuses with no launch, PENDING polls to READY, FAILED tears down and relaunches once, ...`. Listing each branch/case verbatim is noise that restates the test code. The same applies to summaries: name the behavior, do not transcribe the test matrix.

### Formatting commands and output

Put commands and their key output in a fenced code block, not crammed inline in a sentence. Wrap long commands across lines with a backslash. Keep the prose explanation outside the block. For example, write:

````
```
buck2 build //mitra/projects/diffusion_llm/eval:gsm8k_eval_cli \
      "//mitra/projects/diffusion_llm/eval:eval_lib[typecheck]"
-> exit 0 (BUILD SUCCEEDED)
```
The `gsm8k_eval_cli` binary builds and `eval_lib` passes Pyre typecheck cleanly.
````

not a single inline line like ``buck2 build ... "...[typecheck]" -> exit 0 ...``. The same applies to test commands and their `Pass N` result, and to any multi-step command sequence in a summary.

Exercise the real path and show evidence (the Meta test-plan bar). "It builds" or CI-only alone is not enough unless the change genuinely has no behavior to exercise. Same hygiene as summaries: no planning cruft, no em-dashes.

## Code in the diff

The diff's own comments and docstrings follow the same hygiene: keep technical rationale, but no task IDs, no ADR-N, no Spike-N, no "researched <date>", no spec/doc paths, no "master T...", and no em-dashes.

Also remove bare internal project acronyms and labels that only make sense against the planning docs: counter-metric tags like `C1`/`C2`/`C3`/`C4`, gate labels like `Gate-1`/`Gate-2`/`G1`, and perf labels like `P1`..`P5`. Either say what it is in plain words (e.g. `C4 numerical-stability guard` becomes `NaN/Inf guard`, `C3 validity` becomes `answer-extraction validity rate`, `Gate-1` becomes `the GSM8K reproduction check`) or drop the label. This applies to code comments AND the title/summary/test plan.

Exception: keep required external attribution that the tooling expects, such as Citrine ML-efficiency lint tags (e.g. `# Citrine C7: use .to("cuda")`). Those are not project jargon.

### Hold a high bar for what earns a comment

**The default is no comment.** A comment earns its place only by saying something the code cannot: a non-obvious invariant, an external constraint, a gotcha a future reader would otherwise "clean up" and break. Naming and structure carry the rest. Most comments an AI wants to write are restating the line below them, and they read as slop.

Delete a comment if any of these is true:

- **It restates what the line plainly does.** `# Warning rather than info` above `logger.warning(...)`, `# Increment the counter` above `count += 1`, `# Loop over the parameters` above a `for param in ...`. The code already said it.
- **It explains the change rather than the code.** "Fixed per review", "switched from X to Y because the old way double-counted", "this used to use the bool flag". That rationale belongs in the diff summary, and it goes stale the moment the diff lands: a reader a year from now has no "before" to compare against.
- **It repeats a nearby docstring.** If the function's docstring already states the rule, do not restate it at the call site.
- **It justifies a decision to a reviewer.** Comments are for the next engineer reading the file, not for the person reviewing the diff today. Answer reviewers on the thread, not in the source.
- **It says something obvious from types or names.** `# config is optional` above `config: Config | None`.

When a comment IS warranted, write it as tightly as possible: usually one line, rarely more than two. Say the constraint, not the story. Prefer the load-bearing clause over the full explanation.

- Bloated: `# A replicated parameter has to hold identical values on every rank, so its seed must not depend on the rank. A sharded one holds a distinct slice, so it varies by rank. Seeding per parameter rather than once keeps this correct even when ranks hold uneven shard sizes and would otherwise desynchronise.` (the first two sentences are visible in the branch directly below)
- Tight: `# Seeded per parameter rather than once, because uneven shard sizes desynchronise a shared stream.`

Smell tests, in order of how often they fire: a comment whose first words echo the identifier on the next line; a comment containing "rather than", "instead of", or "used to" about the code's own history; a comment longer than the code it describes; a comment that would still be true and useful if deleted.

Apply the same bar to test comments. A test name should carry the intent; a comment is for the non-obvious reason a specific value or case was chosen (`# 3, not 6: the suggestion has to be usable at the requested tp`), not a restatement of the assertion.

## No references to things that do not exist in fbcode

Do NOT reference external tools, scripts, repos, or systems that do not exist in fbcode, in the title, summary, test plan, OR code comments/docstrings. A reviewer (or a future reader) cannot look them up, and "we do it the way X does" is not reviewable when X is not in the codebase. Describe what the code does in its own terms instead.

- Bad: `Mirrors workbench's gen-tls-cert.sh` / `(workbench-style)` / `ported from <some external repo>` / `like <external tool> does`.
- Good: say what the code actually does, e.g. `Runs tlscertreq --mode=sandbox-partitioned and publishes the partition cert whose SAN carries this host's access name`.

This is about provenance to things outside fbcode. Real Meta/fbcode artifacts (a `tlscertreq` binary, a service, an internal wiki/URL, a `//path:target`) DO exist and are fine to name, and external concepts a reader needs (a paper, an algorithm) should be hyperlinked per the Summary rules. The thing to cut is a comparison or attribution to a tool/script/repo that is not in fbcode and that a reader cannot open.

## Mechanics

- Edit diff fields on Phabricator (these survive a later `jf submit`):
  `meta phabricator.diff update -n D<n> --title="..." --summary="..." --test-plan="..." --add-tasks=T<n>`
- One diff per logical change. For a stack, apply review fixes to the owning commit and restack (see the `stack-review` skill). Distribute comment-only cleanups across a stack with `sl absorb` after a `--dry-run` and explicit approval.
- Publishing drafts: publish with `jf submit -s --no-draft`. If it reports diffs as "updated" but `sl ssl` still shows them `Unpublished`, it skipped them as unchanged - re-run with `--no-skip`, or publish explicitly with `meta phabricator.diff publish -n D<n>`, to force the draft->published transition. `meta phabricator.diff action --request-review` does NOT publish a draft (it is rejected on an "unreviewable state" diff); it only re-requests review on an already-published diff. After publishing, verify with `sl ssl` (look for `Needs Review`, not `Unpublished`), not just the `jf submit` output.

## After authoring: clear the signals

Writing the diff well is half the job; the other half is getting it to a clean signal state so a reviewer (human or automated) can actually approve it. Once the diff is published, drive every gating signal to green: CI signals, automated AI reviews (Devmate inline comments, Mitra Code Review), Arctic insights, and governance/RADAR rules (the "Code change is eligible" suppression rule, CodeHub coverage, CRS).

Do this with the **`clearing-diff-signals`** skill (its companion). Key rules it enforces, which every authored diff must also satisfy:
- **No static-analysis suppressions in changed lines** (RADAR "eligible" rule): no `pyre-ignore` / `pyre-fixme` / `HH_FIXME` / `@lint-ignore` / `DO_NOT_USE` / `Allow*ToProd*` / `AutoCanaryRequirements` / `UNSAFE_CAST`. Remove them with a real fix (e.g. `cast(Any, obj).attr` for a stub-missing attribute - NOT `getattr(obj, "literal")`, which pyre resolves like `obj.attr` and still errors), not a relabel; then `arc pyre check` the target, since a removed `pyre-*` may have hidden a real type error (the typecheck is its own CI signal). In a stack, fix at the diff that introduces the suppression so that diff is clean.
- **Address automated + human review comments**: fix the actionable ones at the owning diff, reply on each thread, and validate AI advice before applying it (it can be wrong). "AI Approval - not covered by CodeHub projects" is ownership governance, not a code defect - it clears via the right `#project` reviewer.
- **Resubmit preserving metadata**: `jf sync -s` before `jf submit -s --no-draft` so the resubmit doesn't clobber Phabricator field edits, then verify with `sl ssl`.
