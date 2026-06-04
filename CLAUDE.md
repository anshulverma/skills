# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A personal collection of Claude Code **skills** — each skill is a directory of Markdown
files (no compiled code, no test suite, no build step). The content *is* the product:
prose and protocols that get loaded into a Claude Code session as instructions.

There is currently one skill, `auto-plan/`. New skills are added as sibling directories.

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

## Output locations (written into the target project, not this repo)

When the skill runs, it writes artifacts into the project being planned:
`docs/auto-plan/{specs,plans,reports}/` and `docs/adr/NNNN-<slug>.md`.
Filenames are date-prefixed `YYYY-MM-DD-<topic>-*`.
