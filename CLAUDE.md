# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A personal collection of Claude Code **skills** — each skill is a directory of Markdown
files (no compiled code, no test suite, no build step). The content *is* the product:
prose and protocols that get loaded into a Claude Code session as instructions.

The skills are `auto-plan/` (an autonomous planning orchestrator), `auto-research/` (an
autonomous experimentation loop, ported from github/awesome-copilot), `diff-authoring/`
(Phabricator diff conventions), `i-have-adhd/` (an output-shaping style skill, ported from
ayghri/i-have-adhd), `monk/` (whole-chain diff review), `pr-authoring/` (GitHub PR
conventions), and `sdd/` (spec-to-code pipeline). New skills are added as sibling
directories.

## How skills are deployed

Skills are activated by symlinking each skill directory into `~/.claude/skills/`:

```
~/.claude/skills/auto-plan -> /home/anshulverma/workspace/skills/auto-plan
```

Because it's a symlink, edits in this repo take effect immediately — no copy or rebuild.
A skill directory MUST contain a `SKILL.md` whose YAML frontmatter (`name`, `description`)
is what Claude Code matches against to decide when to invoke the skill. The `description`
is the trigger — it must say *when* to use the skill, not just what it does.

## When editing or creating skills

Use the `superpowers:writing-skills` skill — it is the authority on skill structure,
frontmatter conventions, and verifying a skill works before deployment. Invoke it before
making non-trivial changes here.

## Architecture of the `auto-plan` skill

`auto-plan` is an autonomous planning orchestrator. `SKILL.md` is the orchestrator's
playbook; the other Markdown files are **prompt fragments** that the orchestrator reads
and pastes verbatim into sub-agents it dispatches via the `Agent` tool. Understanding the
split between orchestrator and sub-agent prompts is the key to working here:

| File | Role | Pasted into |
|------|------|-------------|
| `SKILL.md` | Orchestrator control flow (Phases 0–4), state schema, flags | (the main session) |
| `GRILLER-PROTOCOL.md` | How a Griller sub-agent interrogates one design branch | Griller agent prompt |
| `GRILLER-RESPONSE-TEMPLATE.md` | Exact section headers the orchestrator parses back | Griller agent prompt |
| `WRITER-SPEC-PROTOCOL.md` | Structure for the design spec | Writer agent prompt |
| `WRITER-PLAN-PROTOCOL.md` | Structure for the implementation plan | Writer agent prompt |
| `SPEC-REVIEW-CHECKLIST.md` | Pass/fail criteria for the spec | Reviewer agent prompt |
| `PLAN-REVIEW-CHECKLIST.md` | Pass/fail criteria for the plan | Reviewer agent prompt |
| `FINAL-REVIEW-CHECKLIST.md` | Cross-cutting review of all artifacts | Reviewer agent prompt |
| `HARDENING-PASS-PROTOCOL.md` | How a Hardening Pass agent reviews-and-patches the full artifact set in one pass (`--harden`) | Hardening Pass agent prompt |
| `HARDENING-PASS-RESPONSE-TEMPLATE.md` | Exact section headers the orchestrator parses back from a pass | Hardening Pass agent prompt |
| `CONVERGENCE-JUDGE-CHECKLIST.md` | Material-vs-minor rubric + CONVERGED/NOT CONVERGED format | Convergence judge agent prompt |

Flow: the orchestrator builds a branch skeleton, dispatches **Griller** sub-agents (one per
uncertain design branch, parallel on the first iteration) to auto-answer questions, collects
their structured responses, loops until no branches remain uncertain, then dispatches
**Writer** and **Reviewer** sub-agents to produce and validate a spec, ADRs, and an
implementation plan. **Researcher** sub-agents are dispatched for open-ended codebase lookups.

Consequences when editing:

- The Griller's output template (`GRILLER-RESPONSE-TEMPLATE.md`) and the orchestrator's
  result-collection logic in `SKILL.md` (Phase 2 → "Collecting Results") are a contract.
  Changing the section headers in one requires updating the other.
- Sub-agents are non-interactive — Grillers must never ask the user a question; they
  auto-answer or flag `Unresolved`. Only the orchestrator talks to the user.
- The JSON **state file** (`docs/auto-plan/reports/...-state.json`) is the source of truth
  that survives context compression and powers `--resume`/`--redo`. It's rewritten in full
  each iteration (never patched incrementally).
- `--harden` adds a second loop (Phase 5). Two more contracts mirror the Griller one:
  `HARDENING-PASS-RESPONSE-TEMPLATE.md`'s seven headers ↔ the SKILL.md Phase 5 "Collecting Pass
  Results" logic, and `CONVERGENCE-JUDGE-CHECKLIST.md`'s four response headers (`Verdict` /
  `Changes` / `Open Gaps` / `Rationale`) ↔ the SKILL.md judge-collection logic. Changing the
  section headers in one requires updating the other. A **Pass** (outer, `--max-passes`) and an
  **Iteration** (inner, `--max-iterations`) are distinct loops — keep the vocabulary separate.

## Architecture of the `sdd` skill

`sdd` is a **tick-based orchestrator**, not a single-shot skill. It is armed once with
`/loop /sdd <slug>` and thereafter re-enters itself from fresh context on every tick.

| File | Role |
|------|------|
| `SKILL.md` | Tick contract, the five stages, common mistakes, red flags |
| `references/LOOP.md` | Dynamic vs interval loop modes, pacing, exact `ScheduleWakeup` signatures, why no lockfile |
| `references/STAGES.md` | Per-stage `auto-plan` flags, `run.json` schema, the stage 3→4 seam |

Consequences when editing:

- **`run.json` is the router.** Conversation memory is never a valid source of stage or
  progress — context compacts between ticks. Any change that makes a tick infer state from
  anything but disk breaks resumability.
- **One bounded unit of work per tick** is load-bearing. A tick that tries to finish a whole
  stage runs out of context mid-stage and strands partial state.
- **`/loop` is always a recurring cron** (`CronCreate`); omitting the interval defaults it to
  `10m`, it does not switch to self-paced mode. Termination is `CronDelete({id})`, which
  means `run.json` must carry `cron_job_id`. Arm `durable: true` or the run dies with the
  process, and note the 7-day cron expiry on long runs.
- **Stage 4 uses `--resume --harden`, never `--plan-only`.** `--plan-only` routes `0 → 3 → 4`
  and Phase 3 regenerates the plan, destroying the `writing-plans` output from stage 3. The
  state-file reset described in `STAGES.md` is what makes `--resume` harden that plan; the
  first PLAN_HARDEN tick must verify it held.
- `sdd` composes `auto-plan`, `superpowers:writing-plans`, and
  `superpowers:subagent-driven-development`. Changing `auto-plan`'s flag table or state schema
  requires updating `references/STAGES.md`.

## Architecture of the `monk` skill

`monk` is a **review protocol**, not an orchestrator with a state file. `SKILL.md` carries the
phase spine (0 through 4e) and every rule the orchestrator applies itself; the six
`references/` files carry material that is either too long to inline or is pasted verbatim
into sub-agent briefs.

| File | Role |
|------|------|
| `SKILL.md` | Phases 0-4e, input resolution and flags, annotations, the tier lookup, the four Human Judgment gates including gate 4 (the style-laundering ban), the reporting floor, the caps, verdict mapping, delivery, the agent response schema |
| `references/METHOD.md` | The seven rules, warrant grades A-E, edge kinds, trigger derivation, the closed terminal-class list T1-T6, the negation test, the residual-unknown bound |
| `references/ANTI-PATTERNS.md` | Competing reviewers' prompts quoted at `path:line`, the load-bearing negatives, the style-laundering framing, citing `SKILL.md`'s gate 4 |
| `references/REPORT-TEMPLATE.md` | Exact output structure and both worked examples, byte-identical to the design spec |
| `references/FANOUT.md` | Fan-out threshold, the nine-block stage-1 brief, the stage-2 brief, the response schema, stitching, dedup, the coverage ledger |
| `references/PERSISTENCE.md` | `reviews/D<n>.md` schema, the identity triple, version-over-version classification, the ask protocol, suppression |
| `references/KNOWLEDGE-INTEGRATION.md` | Phase 0 prior selection, the dexter understand-only contract, the KB router and authoring rules |

**One normative owner per concept.** Seven files that each restate the tier lookup, the warrant
grades or the terminal classes will drift, and two drifted copies are worse than one missing
copy because both still read as authoritative. So each shared concept has exactly one owning
file and every other file cites that owner by section name instead of restating it:
`METHOD.md` owns the rules, grades, edge kinds and terminals; `SKILL.md` owns the annotations,
tier lookup, caps and verdict mapping; `FANOUT.md` owns the threshold table and the
concurrency cap; `PERSISTENCE.md` owns the ledger schema and identity;
`KNOWLEDGE-INTEGRATION.md` owns the dexter contract and the KB `confidence` values. Adding a
fact means putting it in one file and pointing at it from the others.

Three duplications are deliberate, because at the moment each is read the other copy is not in
context:

| Duplicated block | Sites | Why both copies exist |
|---|---|---|
| Agent response schema headers | `SKILL.md` ↔ `references/FANOUT.md` | `FANOUT.md` is pasted into the sub-agent brief; `SKILL.md` is what the orchestrator parses the return with |
| Verdict mapping table | `SKILL.md` ↔ `references/REPORT-TEMPLATE.md` | the report is written from the template alone, with tiering already decided |
| Killer vocabulary tokens | `references/METHOD.md` ↔ `references/PERSISTENCE.md` | the ledger's `killer` field is a closed enum and has to be checkable from the persistence file alone |

Each pair must stay byte-identical. Task 9 of the build plan diffs all three; after editing one
side, extract both blocks and `diff` them again rather than eyeballing it.

Consequences when editing:

- **The response schema is a parsing contract.** Its six headers (`### COVERAGE`, `### DELTA`,
  `### CHAINS`, `### OPEN-ENDS`, `### UNPROVEN-FACTS`, `### ABANDONED`) must match across both
  sites. Changing one without the other makes the orchestrator silently drop a whole section of
  every agent's return.
- **Finding identity is `(file path, enclosing symbol, terminal failure class)`**, never
  `file:line`. `line_at_raise` is stored for the report and is never matched on. Changing that
  key is not a refactor: it orphans every ledger entry, every suppression and every
  knowledge-base backlink written before the change.
- **The dexter escalation is understand-only, and that is a safety invariant.** Phase 3.5 hands
  dexter a single proposition to decide; the fix phase and the `knowledge/` write are suppressed
  at invocation, the working copy must not be modified, and probes are read-only, local and
  single-host by default. A reviewer that repairs the code it is reviewing has destroyed its own
  evidence, so monk banks any resulting entry itself rather than letting dexter do it.
- **The 0.5 to 0.8 confidence band is published and demoted, never dropped.** Adding a
  confidence threshold or a filter that hides conditional findings is the change a future
  maintainer is most likely to make, and it reproduces the exact failure monk was built to fix.
  The reporting floor and the caps are the noise control.
- **Phabricator stays strictly read-only while the skill writes and git-commits to
  `~/workspace/investigations/`.** Both halves are load-bearing: monk never posts, so there is
  no decline channel, so the local ledger and the batched ask are the only feedback loop it has.
- monk is markdown-only: no scripts, no plugin manifest, no non-markdown artifact.

## Output locations (written into the target project, not this repo)

When `auto-plan` runs, it writes artifacts into the project being planned:
`docs/auto-plan/{specs,plans,reports}/` and `docs/adr/NNNN-<slug>.md`.
Filenames are date-prefixed `YYYY-MM-DD-<topic>-*`.

`sdd` keeps its whole run under `~/.claude/docs/sdd/<slug>/` (`run.json`, `spec.md`,
`questions.md`, `ledger.md`, and a nested `docs/auto-plan/` tree). It invokes `auto-plan` with
cwd set to that directory, which is what redirects auto-plan's repo-relative output there.
Nothing is written into `fbsource`.

`monk` writes nothing into this repo at runtime. Its per-diff findings ledgers go to
`~/workspace/investigations/reviews/D<number>.md`, and confirmed findings graduate into
`~/workspace/investigations/knowledge/` and `LESSONS.md`, the same git-backed repo dexter
uses. It creates `reviews/` on its first run; do not pre-create it here.
