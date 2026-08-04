# skills

A personal collection of [Claude Code](https://claude.ai/code) **skills**. Each skill is a
directory of Markdown files that get loaded into a Claude Code session as instructions — there's
no compiled code, build step, or test suite. The content *is* the product.

## Skills

| Skill | Description |
|-------|-------------|
| [`auto-plan`](auto-plan/SKILL.md) | Autonomous planning agent. Wraps grill-with-docs with contextual auto-answering, iterative deepening, and sub-agent orchestration to produce fully-grilled specs, ADRs, and implementation plans. With `--harden`, it re-runs the whole flow across fresh-context passes — filling gaps and hardening the plan until a numeric instability score converges to 0 — and emits a convergence chart alongside the report. |
| [`auto-research`](auto-research/SKILL.md) | Autonomous iterative experimentation loop for any programming task with a measurable metric. Guides the user through defining a goal, metric command, scope, and constraints, then runs an autonomous edit → commit → measure → keep-or-revert loop on an isolated branch — advancing only on improvements — and reports the results. Ported from [github/awesome-copilot](https://github.com/github/awesome-copilot/blob/main/skills/autoresearch/SKILL.md) (MIT, by luiscantero), inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch). |
| [`diff-authoring`](diff-authoring/SKILL.md) | How to write a Phabricator diff a reviewer can actually review: a tagged title (no task IDs), a goal-first, scannable, self-contained summary that hyperlinks external concepts, and a diff-specific test plan with real evidence (MAST jobs pasted as bare MLHub run URLs so they embed). Keeps planning cruft and AI-tells (em-dashes) out of titles, summaries, test plans, and code. |
| [`i-have-adhd`](i-have-adhd/SKILL.md) | Shapes output for a reader with ADHD: lead with the next action, number multi-step work, restate state across turns, suppress tangents, give specific time estimates, and make wins visible. Manual-invoke only (`disable-model-invocation: true`) — turn it on with `/i-have-adhd`, off with "stop adhd mode". Ported from [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd) (MIT, by Ayoub Ghriss). |
| [`monk`](monk/SKILL.md) | Whole-chain diff review. Holds each causal chain end to end in one reasoner instead of splitting it across per-lens reviewers, grades every link with the citation that grade demands, and reports Must Fix / Human Judgment / Decisions to Validate against a measured ~1.7% base rate, so "nothing found" is a first-class, evidence-bearing outcome rather than a failure. Never writes to Phabricator; persists findings per diff under `~/workspace/investigations/reviews/` and graduates confirmed ones into the dexter knowledge base. |
| [`pr-authoring`](pr-authoring/SKILL.md) | How to write a GitHub pull request a reviewer can actually review: a clear title matching the repo's convention (no issue numbers stuffed in it), a concise self-contained description that leads with the goal and hyperlinks every external reference, issues linked via closing keywords (`Closes #123`), and a PR-specific `## Testing` section carrying real evidence. Keeps planning cruft and AI-tells (em-dashes) out of titles, descriptions, testing sections, and code. The GitHub-PR sibling of the Phabricator-focused `diff-authoring` skill. |
| [`sdd`](sdd/SKILL.md) | Spec-Driven Development. Drives one approved design spec from "approved" to "implemented" across many self-paced `/loop` ticks: a single interactive question gate, then spec hardening via `auto-plan --harden`, plan authoring via `writing-plans`, plan hardening via `auto-plan --resume --harden`, and execution via `subagent-driven-development` — one bounded unit of work per tick, all state on disk so the run survives compaction and restarts. Ends itself with `ScheduleWakeup({stop: true})`. |

## Installation

Skills are activated by symlinking each skill directory into `~/.claude/skills/`:

```sh
ln -s "$PWD/auto-plan" ~/.claude/skills/auto-plan
```

Because it's a symlink, edits in this repo take effect immediately — no copy or rebuild.

## Anatomy of a skill

A skill directory must contain a `SKILL.md` whose YAML frontmatter declares `name` and
`description`. The `description` is the trigger Claude Code matches against to decide when to
invoke the skill, so it states *when* to use the skill, not just what it does.

Skills may include additional Markdown files. In `auto-plan`, those extra files are prompt
fragments the orchestrator pastes verbatim into sub-agents it dispatches (Grillers, Writers,
Reviewers, Researchers). See [`CLAUDE.md`](CLAUDE.md) for the full architecture.

## Contributing

Use the `superpowers:writing-skills` skill when creating or editing skills — it's the authority
on structure, frontmatter conventions, and verifying a skill works before deployment.
