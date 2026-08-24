---
name: docket
description: Use when reviewing a Phabricator diff stack one diff at a time, when a reviewer needs a per-diff verdict plus the exact comments to post and an accept-or-send-back ruling, when walking a stack and pausing between diffs ("next diff"), or when asked to review a stack for someone who does not know the codebase.
---

# docket

A docket is the ordered list of cases before a court: worked one at a time, each ending in a
ruling. This skill is the reviewer's bench for a diff stack. **`monk` finds defects; `docket`
rules on them.**

It does three things `monk` does not: it **paces** the review (one diff per turn, then stop),
it **renders** a fixed card, and it **converts** surviving findings into postable comment text
plus an accept-or-send-back decision.

**REQUIRED SUB-SKILL:** `monk` supplies every defect claim. **REQUIRED for comment wording:**
`diff-comment-authoring`. **For judging whether a summary is adequate:** `diff-authoring`.

## When to use

- A stack (or single diff) needs reviewing and the human wants to work it diff by diff.
- The reviewer must decide **accept vs send back** and post comments, not just read findings.
- The reader does not know the codebase and needs the vocabulary defined.

Not for: writing your own diff (`diff-authoring`), replying to comments on your own diff
(`diff-comment-authoring`), or driving CI to green (`ci-patrol`).

## The Iron Rule

**Every claim on a card traces to a `monk` finding that survived `monk`'s reporting floor, or
to a command you ran this session and cite. Nothing else reaches the card.**

This is the whole point of the skill. Measured baseline: three freehand reviews of the same
18-line diff answered one countable question ("how many configs set `hosts: 4`?") as *16 of
17*, *8 of 11*, and *10 of 13*. All three stated it with full confidence, all three made it the
top blocking comment, and all three were leading with a claim `monk` had killed on a cited
negation. A review that over-emits costs the author's trust, and you only get to spend that
once.

## Flow

```
Phase 0  Resolve the docket      pin stack order locally, one row per diff
Phase 1  Run monk, whole stack   once, up front, tripwire before any card
Phase 2  Render ONE card         then stop and wait
Phase 3  On "next"               render the next, carry forward what changed
```

### Phase 0 — Resolve the docket

Pull every diff so its content is readable locally, then pin the order:

```bash
cd <repo>
sl log -r D<top> --reason "pull stack top for review - sl help log"
sl log -r "D<top>~<N>::D<top>" --reason "list stack in order - sl help log" \
  -T "{node|short}|{phabdiff}|{author|user}|{desc|firstline}\n"
```

Reading a diff at its own revision, and at the previous one:

```bash
sl cat -r D<n> <path>        # new version
sl cat -r 'D<n>^' <path>     # old version
sl diff -r 'D<n>^' -r D<n>   # the change
sl cat -r D<top> <path>      # what actually ships
```

Four things that bite, all seen in real stacks:

| Gotcha | How it shows | What to do |
|---|---|---|
| Phabricator's child list is reverse-ordered | "position 2 of 21" with parents listed newest-first | reverse it, then confirm against the local graph |
| An off-mainline sibling | two local commits carry the **same** diff number, different hashes | the one in `~N::top` is the mainline; the other is stale — say so on its card |
| A different author mid-stack | `{author|user}` changes | do not apply the stack's invariants to it |
| `A::B` revset explodes | `abort: revset query scanned over 100000 commits` | the diffs are on divergent bases; use `D<top>~N::D<top>` |

Emit the resolved docket as a table before anything else. That table is the agenda.

### Phase 1 — Run monk once, over the whole stack

Run `monk` across every diff **before rendering the first card**, not per card.

Why up front: files in a stack are commonly edited by several diffs. A defect raised on diff 2
may be fixed by diff 12, and a config committed at diff 13 may be what makes diff 2's finding
fire. `monk`'s `still-true-at-stack-top` check and its trigger-satisfiability check both need
the top of the stack in view. Per-card runs re-derive the stack facts N times and still can't
answer either question.

Two rules that are not optional:

1. **`monk`'s Must Fix tripwire fires before a card is rendered, never after.** More than two
   provable findings on one diff means re-verify that diff adversarially first. In the stack
   this skill was built from it fired twice and cut 11 chains to 3 — one of which had a privacy
   argument with its sign inverted. A card built on that would have sent the reviewer to post
   comments on findings that do not hold.
2. **An unproven fact carrying `depends: <chain>` is a residual ASSUMED link for that chain.**
   Agents park significance-bearing unknowns under `UNPROVEN-FACTS` while grading every link
   READ, which reads mechanically as zero residual and inflates Human Judgment into Must Fix.
   Count it. This correction was needed twice in one stack.

### Phase 2 — Render one card, then stop

Present exactly one diff. Do not batch, do not preview the next one, do not summarise the
stack. Stop and wait for the human.

## The card

The output **is** these slots, in this order. Fill every one.

````markdown
# D<number> — `<title>`

<files>, +<added>/-<removed>. <how it was reviewed>

## Background you need to read this
<Only on the first card, and on any later card that introduces new vocabulary.
Define every system, acronym and datatype the rest of the card uses. Assume zero
codebase knowledge.>

## Diff Summary
<Bullets, one per thing the diff does. Plain language: NO file paths, NO symbol
names, NO line numbers. A reader who has never seen this code should understand
each bullet. Save the citations for the Risks slot.>

## Responsibilities: N
<The count of bullets above, then one line: is this one job or several, and if
several, where the natural seam is. A diff doing 4+ unrelated things is worth
saying so even when every one of them is correct.>

## Intent
<What the author says it is for. 1-3 lines.>

## Does it do what it says: Y | N
<If N: each mismatch as one bullet — the claim, then the fact that contradicts it,
with its citation. Rule 7 findings live here.>

## Is it well tested: Y | N
<If N: name the specific hole and what it lets through. A test that cannot fail is
worth calling out by name. Say what IS covered too — a bare N reads as lazy.>

## Risks or potential violations
<One numbered bullet per surviving monk finding, highest terminal severity first.
Each: what breaks, the mechanism in one sentence, the citation, and whether it is
live at stack top or inert here.>

## Checked, not commenting on
<Chains pushed and killed, and why. This is where diligence becomes visible and
where the reviewer is stopped from wasting the author's time.>

## Ruling: Accept | Accept with comments | Request changes
<Two or three lines of reasoning, tied to the table below.>

### Topline comment
<One line: the action and the single reason for it. Then, if there are smaller
mismatches, an "Also" list of bare facts, one line each.>

### Inline comments
<Per comment: a one-line note on what it covers so the reviewer can triage without
reading it, then the anchor, then the code at that line as a short snippet, then the
comment text in a fenced block.>
````

**"Checked, not commenting on"** is required even when short. It is where a refuted candidate
goes at no cost to the author, and it is the only thing distinguishing a careful review from a
short one.

## Writing the comments

Two shapes, and they are not the same shape.

**The topline** is the action plus the single reason for it, on one line. Then, if there are
smaller mismatches, an `Also` line — an enumerated list when the items are crisp, a bare
gesture when they are not. Both are honest; padding a gesture into a list is not.

```
Back to you due to the possible loss of cached scores on reload and on restart

Also some things in the diff summary didn't line up with the contents.
```

```
Back to you due to the potential UID leak in logs

Also, a few things that didn't line up in the diff summary:
1. the components list names two files that aren't in this diff
2. test_sid_to_uid_client doesn't exist. Maybe it was removed later?
```

**An inline comment asks a question.** That is the whole of it. Three real ones, in ascending
length — and the length is set by how far the reader has to travel, not by how much you found:

```
is the per-SID assignment here meant to replace rather than merge?
```

```
I believe if this fails it would get classified as a scoring failure downstream right? Is that intentional?
```

```
Wondering if there is a race condition here since `_rank_records` is cleared first [here](https://www.internalfb.com/code/fbsource/[<full-hash>]/fbcode/path/to/file.py?lines=135). So could a restart or a second job on the same ds, overwrite what an earlier flush wrote?
```

The first needs no link: the thing it asks about is at the anchor. The third needs one, because
the reader has to see a second place before the question means anything.

| Rule | Why |
|---|---|
| Ask, never assert | The author knows this code; a question gets an answer, an assertion gets a defence |
| Ask about **intent** — "is this meant to…", "is that intentional?" | Presumes there was a reason, which is usually true and always cheaper than being wrong in public |
| Hedge in the first person — "wondering if", "I believe … right?" | You are working from a read, not from having run it |
| **Phrase the consequence as a question too** — "so could a restart overwrite what an earlier flush wrote?" | Stating the consequence is the assertion again, one step later |
| Link only when the reader must see a **second** location | A link to the line the comment is already attached to is noise |
| Never name the terminal, the severity or the tier | That is the card's vocabulary, for the reviewer. The author needs the observation |
| Merge related nits on one file into one comment | Two comments on one docstring reads as pedantry |
| Fenced code block, never a blockquote | The reviewer pastes this; `>` renders as a left bar and breaks the paste |
| A one-line note above each comment, in the card | Lets the reviewer triage without reading the comment |

**Do not trace the mechanism.** Which handler catches what, which sink formats it, why the
negation fails — all of that belongs in the card's Risks slot, written for the reviewer
deciding whether to post. In the comment it does the author's thinking for them, on their own
code. Name what you saw, point once if a pointer is needed, and ask.

### Show the code

Every inline comment carries a snippet of the anchor line plus just enough around it to be
legible — one to five lines, language-tagged, with the anchor line marked when it is not
obvious which one it is:

````markdown
**`preselected_scores_cache.py`, line 225** — inside `_read_snapshot_into`

```python
for sid, pairs in payload.items():
    out[int(sid)] = {int(a): float(s) for a, s in pairs}   # <-- line 225
```

```
is the per-SID assignment here meant to replace rather than merge?
```
````

The snippet is **for the card, not for the comment.** Phabricator already renders the code
beside an inline comment, so pasting it into the comment is noise the author has to scroll
past. It is in the card because the reviewer is deciding whether to post without opening the
file, and a comment about a line you cannot see is a comment you cannot judge — which is how a
wrong comment gets posted.

Pull it at the reviewed revision so it matches the permalinks:

```bash
sl cat -r D<n> <path> --reason "snippet for a review comment - sl help cat" | sed -n '<from>,<to>p'
```

Permalink form, using the full 40-character hash of the revision reviewed:

```
https://www.internalfb.com/code/fbsource/[<full-hash>]/<repo-relative-path>?lines=<N>
```

Line numbers drift between versions, so anchor the comment on the enclosing symbol and mark the
line approximate; the permalink is what stays correct.

`diff-comment-authoring` governs the rest: no praise opener, no restating what the author wrote,
no verification dump, no volunteered extras.

## Ruling

| monk verdict on the diff | Default ruling |
|---|---|
| Must Fix ≥ 1 | Request changes |
| Human Judgment that goes live at stack top (privacy, correctness, data loss) | Request changes |
| Human Judgment only, all conditional on facts only the author knows | Accept with comments |
| Clean, but an Improvement is a one-line fix in a file the diff already touches | Accept with comments |
| Clean | Accept |

"Accept with comments" means the comments are worth asking for in this round but are not
worth blocking on. Say which it is; do not let a reader guess whether you are blocking.

Two overrides, both learned the hard way:

- **A materially wrong summary is Request changes even when the code is clean.** The summary is
  what other reviewers, and any privacy or security reviewer, actually read. A summary naming
  components that do not exist, or a test plan crediting a test that was deleted, misleads
  everyone downstream of you.
- **A diff that is a no-op against the mainline is not Accept.** Say it cannot apply and should
  be dropped from the stack.

State the ruling as a decision, not a hedge. "Looks reasonable, some concerns" is not a ruling.

## Scope

Lint owns formatting, import order, line length and naming — none of it becomes a comment. Both
baseline runs filed `arc f` and a PEP 701 quoting nit as review comments on an 18-line diff; one
of them had already confirmed the syntax parses on the target platform and filed it anyway.

Quantitative claims ("N of M configs", "4x the GPUs") carry the command that produced them or
they do not go on the card.

## Common mistakes

| Mistake | Why it costs you |
|---|---|
| Rendering all diffs at once | The human asked to pace it; a wall of cards is unreadable and unactionable |
| Comment count scaling with reading effort | 10 comments on 18 lines reads as noise, and the real finding gets lost in it |
| Re-deriving a fact monk already settled | monk cited it; restating it unsourced makes it look weaker than it is |
| Dropping "Checked, not commenting on" | The review becomes indistinguishable from a shallow one |
| Blockquotes for comment text | Breaks the paste, which is the entire deliverable |
| Hedged Y/N | The two questions are the reason the card exists |

## Red flags

- About to post a comment that traces to no `monk` finding and no command you ran.
- About to state a count, ratio or "N of M" you have not computed this session.
- About to render a second card without being asked.
- Must Fix count on one diff is 3+ and no re-verification has run.
- The "Risks" section is longer than the diff.

## Delivery

Default: the card in the conversation. For a long card, or on request, write it to a paste and
reply with the link plus a 3-line digest:

```bash
<render card to /tmp/docket-D<n>.md>
pastry --md --private --title "docket: D<n>" < /tmp/docket-D<n>.md
```

**Both flags are required.** `--private` restricts the paste to its author: a card names
unposted findings, refuted candidates and a send-back recommendation about someone else's work,
and none of that should be world-readable before the reviewer decides what to say. `--md`
uploads it as markdown; without it every table, heading and fenced block renders as literal
source and the card is harder to read than the terminal output it replaced.

Hand back the returned URL with `?view=markdown` appended:

```
https://www.internalfb.com/phabricator/paste/view/P<number>?view=markdown
```

When rendering a whole stack, dispatch one agent per diff so each card is built in its own
context, and return a table of `D<number> | verdict | paste URL` for the human to work through
one at a time.

`docket` posts nothing to Phabricator. It produces the text; the human posts it.
