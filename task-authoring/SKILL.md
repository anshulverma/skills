---
name: task-authoring
description: Use when creating, rewriting, or cleaning up a Meta Task (meta tasks.task create / update), including a plan's master task and its subtasks, bug and follow-up tasks, and task comments; and whenever a task's evidence comes from other people's jobs, diffs, pastes, or docs.
---

# task-authoring

A task is read by an assignee, human or agent, who has never seen the plan, the conversation, or the investigation behind it. Write it so they can execute from the task alone, and so it reads as the owner's own work: what is true, what to do, how to tell it is done. Never where the information came from.

This is the task sibling of `diff-authoring`. Its rules on defining terms at first use, no planning cruft, no em-dashes and no hard-wrapping apply here unchanged. Where a planning skill's template (for example `mp-to-tasks`) prescribes different sections, this skill governs the text.

## Title

- The outcome, imperative and specific: `Make grpo_advantages sync-free`, not `grpo.py cleanup` or `Look into advantages`.
- Area tags taken from the area's existing tasks and diffs, never carried in from elsewhere. `[Master]` goes first on a plan's master task.
- No task IDs, wave numbers, or em-dashes.

## A subtask is

These sections, in this order, and nothing else:

1. `## Goal`: one or two lines, the outcome and why it matters.
2. `## Evidence` (or `## Today`): the current state as numbers, each next to the artifact that shows it.
3. `## What to build`: the scope, with code pointers pinned to a revision. Numbered steps only when their order matters.
4. `## Acceptance criteria`: `[ ]` items, each checked by exercising the real path, each with a target number and the run or command that shows it.
5. Only when true for this task: `## Constraints` (rules the assignee must obey, such as one MAST job at a time), `## Needs a human` (one line naming the decision or access an agent lacks, paired with the `ready-for-human` tag), `## Coordination` (a named edit conflict with a sibling, by T-number), `## Out of scope`.

Budget: about 30 lines. Past 40, the task is carrying the working: keep each conclusion and its artifact, drop the derivation. Define a term inline at first use instead of adding a glossary section.

## A master task is

A high-level summary of the goal and of how each subtask moves it. It holds no action items.

1. `## Goal`: the outcome, the target, and the one or two numbers that define done.
2. One short section named for what it holds (`## Why it is slow`, `## What is missing`): the obstacle in a few bullets, enough to see why these subtasks are the right ones. No derivations, metric definitions, or tables of raw measurements; those live in the subtasks that act on them.
3. `## Subtasks`: one table listing every child, `Task | How it moves the goal | Expected gain | Readiness | Blocked by`. Update it in the description whenever a child is added, merged or closed.

A sentence in a master that tells someone to do something is an action item. Move it into the subtask that owns it; if no subtask does, create one (`--parent`, readiness tag) and add its row. Rules every subtask must obey while verifying go into each subtask's `## Constraints`, because an assignee opens one task, not the master.

## Fields carry structure

| Fact | Set with | Not in the body as |
|---|---|---|
| Parent | `--parent T…` | `## Master T…` |
| Blockers | `--blocked-by` / `--blocks` | a bare `## Blocked by` list |
| Readiness | `--add-tag ready-for-agent` or `ready-for-human` | `## Readiness` restating the tag |
| Linked diffs | `--add-diff D…` | a `Diffs:` line |
| Wave, critical path | the master's Subtasks table | a section in every subtask |

The body mentions a relationship only when that adds a fact: why a blocker blocks, or which function two tasks both edit. Refer to another task by its T-number, never by description ("the sibling scorer task", "the parent task").

## No lineage

The task states facts and cites artifacts. It never says who found something, whose runs, diff or doc it came from, which tool or session produced it, or when you looked.

| Cut | Write |
|---|---|
| What moved Yihua's runs from 150K to 200K | What moved ready-pool runs from 150K to 200K |
| `scoring_capture_stride: 2` (added in D120812247) | `scoring_capture_stride: 2` |
| Baseline and ceilings (measured 2026-09-27) | Baseline and ceilings |
| Code locations (verified at `879e84f69ad1`) | Code locations (at `879e84f69ad1`) |
| Found by the test-fix harness while fixing X | (delete) |

- An artifact is fine whoever made it: another person's MAST job, its profiler trace, the config the launcher uploaded for it. Cite the artifact, and make the run the subject of the sentence, never the person. A URL that happens to contain someone's bucket or unixname is still just an artifact.
- Name a setting by its config knob. Cite a diff only when the assignee has to open it to do the work: to continue it, rebase on it, or revert it.
- Never lift text, tables, conclusions or unlanded code from someone else's doc, paste or commit. Re-derive the claim from jobs or landed code and write it in your own words, or leave it out. Check authorship before citing: `meta phabricator.paste describe --id P…`, `meta phabricator.diff describe -n D…`.
- A claim whose only source was a doc link you removed has lost its citation. Re-derive it from an artifact, or drop it.
- If an existing task's idea or plan comes from someone else's doc or unlanded code, ask the task owner whether to keep it (names and doc links scrubbed) or close it. Do not decide silently either way.

| Rationalization | Reality |
|---|---|
| "The diff number is evidence, not attribution." | It records where the knob came from. The knob name and the job pair are the evidence. |
| "Crediting the author is the honest thing." | Credit reads as building on a colleague's work. The job link already lets anyone check the number. |
| "The date shows how fresh the number is." | The code revision and the job pin it. A date only says when you looked. |

## References

- Every reference is one the assignee can open: a bare URL, or `T…`, `D…`, `P…` (these auto-link). Put a short label before a long URL: `lcfh9qdf (209K): https://…`. Do not use `[text](url)`: it hides the address.
- Pin code pointers to a revision so the line numbers stay right: `https://www.internalfb.com/code/fbsource/[<rev>]/fbcode/<path>?lines=<a>-<b>`.
- If a reference is a local commit, a scratch path, or an unpublished package, say what it contains and that it is unpublished, or publish it first. Never present it as something the reader can open.

## Keep it current

- The description is the current truth. When scope or numbers change, edit it. A comment that contradicts the description leaves two truths.
- No promises of future content ("locations will be added as comments").
- Comments record events: a decision, a result, a blocker cleared.
- Before creating a task, read the parent's children. If one already covers the work, extend it. To merge duplicates, first fold the facts only the duplicate carries into the task that survives, then `meta tasks.task merge --task <duplicate> --into <survivor>`.

## Mechanics

- Read: `meta tasks.task describe --task T… --output json`, and `meta tasks.comment list --task T…`.
- Write: `meta tasks.task update --task T… --title "…" --description file:///abs/path.md` (the file avoids shell quoting), plus `--add-tag`, `--remove-tag`, `--parent`, `--blocked-by`.
- Save the old description to a file before overwriting it, and re-read the live task right before you write. Tasks in an active plan get edited while you draft; if the live text changed since your snapshot, redraft from the live text instead of overwriting it.
- Merging two subtasks of the same parent fails unless you skip the relationship transfer: add `--no-parents --no-subtasks --no-children` to `meta tasks.task merge`.
- The editor re-serializes markdown on save: it escapes `_` and `>`, pads tables, and turns bare URLs into `[url](url)` links, which still show the address. Read the task back after writing.

## Read it back

On the saved text, not your draft:

1. Search for people: names, `her`, `his`, unixnames. Every hit outside a URL is lineage.
2. Search for `D1`: every diff left must be one the assignee opens to do the work.
3. Search for dates and for `measured`, `verified`, `found`, `researched`.
4. Master: every child is in the table, and no sentence assigns work.
5. Subtask: under about 40 lines, every sibling cited by T-number, and the fields agree with the body (the readiness tag against `## Needs a human`).
6. Every acronym is defined at first use, and there are no em-dashes (U+2014) or en-dashes (U+2013).
