---
name: pr-authoring
description: Use when creating or updating a GitHub pull request (gh pr create / gh pr edit, or the web UI). How to write a PR so a reviewer can actually review it: a clear title that matches the repo's convention (no issue numbers stuffed in it), a concise hierarchical self-contained description that leads with the goal and hyperlinks external concepts, issues linked via closing keywords, and a PR-specific testing section with real evidence. Also keeps planning cruft (issue IDs as stamps, ADRs, spike labels, spec paths, dates) and AI-tells (em-dashes) out of titles, descriptions, testing sections, and code comments.
---

# pr-authoring

Write each pull request so a reviewer who has never seen the project can review it from the title, description, and testing section alone. Apply this to every PR you create or update.

This is the GitHub-PR sibling of `diff-authoring` (which targets Phabricator). Same philosophy, GitHub mechanics.

## Title

- Match the repository's existing PR title convention. Skim recent merged PRs first and follow what they do. Common conventions:
  - **Conventional Commits**: `type(scope): summary`, e.g. `feat(auth): add OAuth device flow`, `fix(parser): handle empty input`. Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `build`, `ci`.
  - **Bracketed area tags**: `[area] short specific description`, e.g. `[ci] cache the toolchain download`.
  - **Plain imperative**: `Add retry logic to the upload client`.
- If the repo has no clear convention, default to a plain imperative summary (`Add ...`, `Fix ...`, `Remove ...`). If you are unsure which convention or scope to use, stop and ask the user (offer options), do not guess.
- The title often becomes the squash-merge commit subject. Keep it imperative, specific, and short (aim for ~50 to 72 chars). It is NOT the edited file name.
- Do NOT stuff the issue number into the title. Issues are linked from the body (below).
- Do NOT use em-dashes (`—`). Use a colon or plain words: `fix(parser): handle empty input`, not `fix(parser) — handle empty input`.

## Linking issues

- Link the issue from the PR body using a GitHub closing keyword so it auto-closes on merge:
  `Closes #123` (also `Fixes #123`, `Resolves #123`). Put it on its own line, typically near the end of the body.
- Cross-repo: `Closes owner/repo#123`.
- For a related-but-not-closed issue, reference it without a keyword: `Related to #123`.
- An issue number never appears as a provenance stamp in the title, the prose of the description, or the code. The closing-keyword line is the one place it belongs.

## Description (body)

Lead with the goal, then add only the sections that matter for this PR. Keep it tight (roughly 5 to 10 lines). Bullets over paragraphs. GitHub renders GitHub Flavored Markdown, so use it.

If the repo has a `.github/PULL_REQUEST_TEMPLATE.md`, fill that template out rather than inventing your own headings; map the guidance below onto its sections.

Use a clear visual hierarchy with Markdown headings (`##` for sections, `###` for sub-points when a section needs them); bullets under each heading.

1. **Goal** (always, first): a `## Goal` section, 1 to 2 plain lines saying what the PR does and why.
2. Then only the sections that matter, each as its own `##` heading, chosen from: `## What it adds`, `## What it changes` / `## What it removes`, `## Why` (only if the choice is non-obvious), `## Risk` (what a reviewer should scrutinize), `## Out of scope`. Add `###` subheadings only when a section genuinely has sub-parts.

Rules:
- **Reviewer-oriented**: enough to review, not verbose, not in the weeds.
- **Self-contained**: the reader either understands fully from the description, or follows a clickable reference. No bare internal jargon or project labels (e.g. `C3`, `Gate-2`, `P3`, `Spike-2`) unless you explain it in plain words right there.
- **Every reference must be a clickable link.** Never leave a bare non-clickable token (an artifact path, a job name, a raw identifier) sitting in the text as if a reader could follow it. Make it a link:
  - External model / dataset / algorithm / technique / library: hyperlink the first mention to its docs or paper, e.g. `[LoRA](https://arxiv.org/abs/2106.09685)`, `[Zod](https://zod.dev)`.
  - Issue / PR / commit: `#123` and full commit SHAs auto-link within the repo; `@user` auto-links a user. For another repo, use `owner/repo#123`.
  - CI run, build, deploy, or artifact: link the run/artifact URL (e.g. a GitHub Actions run, a release asset). Do not paste a job name or path as plain text.
  - Wikis, docs, design discussions: link the URL.
- **No planning cruft**: no ADR references, no "part of epic #...", no issue IDs as stamps, no spec/doc file paths, no "researched <date>", no Spike-N labels.
- **Sound human, not AI-generated**: no em-dashes (`—`); use `:`, `,`, `(...)`, or ` - `. Do not over-bold, do not over-structure, vary phrasing. Backtick code symbols. Do not hard-wrap (GitHub reflows paragraphs).

## Testing

GitHub has no dedicated test-plan field, so put this in a `## Testing` section in the PR body (or the template's testing section). Make it specific to THIS PR (not a copy of the project's overall test strategy). Green CI alone is not the bar: name what you ran and show evidence. Pick the category that fits:

1. **Docs / config only, no runnable behavior**: keep it to one short line stating there is nothing to build or run (e.g. `Docs only, no code to build or run.`). Do NOT narrate a manual review or re-list what the description already covers, that is redundant.
2. **Unit / integration tests**: the exact command plus the captured result (e.g. `npm test -> 142 passing`, `cargo test -> ok. 87 passed`, `pytest -> 53 passed`).
3. **Build / typecheck only** (pure refactor, no behavior change): the build or typecheck command and result, leading with why that is sufficient.
4. **Runs a job / service / manual flow** (a script, a deploy, a UI path): run it and report it concisely with logs, screenshots, or run links as clickable references plus the key result. Keep it to a sentence or two, not a log dump. Attach screenshots for UI changes (drag into the body or use `![alt](url)`).

### Formatting commands and output

Put commands and their key output in a fenced code block, not crammed inline in a sentence. Wrap long commands across lines with a backslash. Keep the prose explanation outside the block. For example, write:

````
```
npm run build && npm run typecheck
-> build OK, 0 type errors
```
The bundle builds and `tsc` passes cleanly.
````

not a single inline line like ``npm run build && npm run typecheck -> build OK ...``. The same applies to test commands and their pass count, and to any multi-step command sequence in the description.

Exercise the real path and show evidence. "It builds" or "CI is green" alone is not enough unless the change genuinely has no behavior to exercise. Same hygiene as the description: no planning cruft, no em-dashes.

## Code in the PR

The PR's own comments and docstrings follow the same hygiene: keep technical rationale, but no issue IDs, no ADR-N, no Spike-N, no "researched <date>", no spec/doc paths, no "epic #...", and no em-dashes.

Also remove bare internal project acronyms and labels that only make sense against the planning docs: counter-metric tags like `C1`/`C2`/`C3`/`C4`, gate labels like `Gate-1`/`Gate-2`/`G1`, and perf labels like `P1`..`P5`. Either say what it is in plain words (e.g. `C4 numerical-stability guard` becomes `NaN/Inf guard`) or drop the label. This applies to code comments AND the title/description/testing section.

Exception: keep required external attribution that the tooling expects, such as license headers or lint-suppression tags that a linter mandates. Those are not project jargon.

## Mechanics

- Create a PR with the `gh` CLI; pass a multi-line body via a file to preserve Markdown exactly:
  ```
  gh pr create --title "..." --body-file pr-body.md
  ```
  Use `--draft` while still iterating, and `--base <branch>` if not targeting the default branch. `--body "..."` works for short bodies but a file avoids shell-escaping pain with backticks and newlines.
- Edit fields on an existing PR (the title and body survive subsequent pushes to the branch):
  ```
  gh pr edit <number> --title "..." --body-file pr-body.md
  ```
  `gh pr edit --add-reviewer <user>` / `--add-label <label>` adjust reviewers and labels.
- One PR per logical change. Keep the branch focused; address review feedback with follow-up commits on the same branch (or amend + force-push if the repo prefers a clean history), then re-request review.
