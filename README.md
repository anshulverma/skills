# skills

A personal collection of [Claude Code](https://claude.ai/code) **skills**. Each skill is a
directory of Markdown files that get loaded into a Claude Code session as instructions — there's
no compiled code, build step, or test suite. The content *is* the product.

## Skills

| Skill | Description |
|-------|-------------|
| [`auto-plan`](auto-plan/SKILL.md) | Autonomous planning agent. Wraps grill-with-docs with contextual auto-answering, iterative deepening, and sub-agent orchestration to produce fully-grilled specs, ADRs, and implementation plans. With `--harden`, it re-runs the whole flow across fresh-context passes — filling gaps and hardening the plan until a numeric instability score converges to 0 — and emits a convergence chart alongside the report. |

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
