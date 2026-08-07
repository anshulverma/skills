---
name: diff-comment-authoring
description: How to write a comment or reply on a Phabricator diff. The default is ONE sentence that answers only what was asked. Kills the AI tells in review replies: headers and bold labels on a short answer, praise openers, restating the reviewer's point, verification dumps, and volunteered extras (why you got it wrong originally, which precedent you should have used, related consequences, confirmation you verified it). Trimming obvious slop is not enough; if the reviewer did not ask it, delete it. Use EVERY time you post or reply to a comment on a diff (meta phabricator.diff comment / reply-comment / update-comment), including replies to automated reviewers (Devmate, Mitra Code Review). Companion to diff-authoring (title/summary/test plan, which DO take structure) and clearing-diff-signals.
---

# diff-comment-authoring

A diff comment is a message to a person who is mid-review. They already have the
diff open. Write the way you would in chat: say the thing, then stop.

Apply this to every comment and reply you post on a diff, including replies to
automated reviewers.

## Default shape

**One sentence. No headers. No bold labels. No bullets.**

One sentence is the target, not a lower bound to clear. Two is already unusual;
three needs a reason you could defend out loud.

> Fixed, thanks.

> Done in D115165866.

> Agreed, moved to `mitra/demo_serving` and the file to `source/mitra/release/`.

> Leaving as-is: `--auth` cannot take `-h` as a value, and argparse would reject it anyway.

Before adding a second sentence, ask what question it answers. If the reviewer
did not ask it, delete it.

## Answer what was asked, and nothing else

This is the rule that gets broken most, and it survives every other edit because
each addition feels individually justified. It is not.

Do not volunteer:

- **Why you got it wrong originally.** "I modelled on cu_core instead, which is
  `cu_training`-owned..." Nobody asked. It is self-narration.
- **The precedent you should have used.** Relevant to you, not to them.
- **Related consequences.** "Note the post-land ACL grant is now against X." If it
  genuinely needs saying it is its own comment, or it belongs in the summary.
- **Confirmation you verified it.** They will see CI.
- **What else you changed nearby.**

A reviewer asking "should this be `mitra` instead?" wants one word and the
confirmation. Everything past that is you talking to yourself in their inbox.

## Lead with the disposition

The reviewer wants to know what happened to their comment. Put that in the first
few words, not after a preamble.

- Bad: "Good catch, and thank you for raising this. You are right that the build
  node lacks notifications while test and release both have them. This was
  unintentional..." (the answer has not arrived yet)
- Good: "Fixed, all three nodes notify `oncallteam-mitra_training` now."

Dispositions worth naming plainly: fixed, fixed elsewhere (name the diff),
declining (give the reason in the same breath), already handled, or a genuine
question back.

## Cut

- **Restating their point.** They wrote it. Acknowledging it back in full is
  padding.
- **Verification dumps.** Do not paste build output, test counts, or materialized
  config into a reply. If evidence matters it belongs in the test plan; link it or
  give one line.
- **Root-cause essays.** Say what changed. Mechanism only when the reviewer needs
  it to evaluate the fix.
- **Praise openers.** "Great catch", "Excellent point", "Thanks for flagging" as a
  reflex. A plain "Good catch" is fine occasionally when it is true; it is noise
  every time.
- **Self-flagellation.** One clause of ownership if you broke something. Not a
  paragraph.
- **Consequence asides.** "One thing worth naming for whoever does X later..." If
  it matters, it is its own comment or belongs in the summary.
- **Markdown scaffolding.** Headers, bold run-in labels, and tables on a short
  reply read as generated.

## When structure IS warranted

Rare. Use it only when you are genuinely answering several distinct points at
once, and even then prefer numbered items matching THEIR numbering, one or two
lines each:

> 1. Fixed.
> 2. Declining: the wrapper would have to re-implement the parser's grammar.
> 3. Fixed in D115165865, budget cut from 20s to 5s.

A code block is justified when the exact text is the answer (a command to run, a
signature, the one line that changed). Not to prove you ran something.

## Tone

Plain and direct. No em-dashes (use a colon, comma, or parentheses). Contractions
are fine. Do not hedge, and do not over-qualify a decision you are confident in.

Disagreeing is normal and should be brief: state the technical reason, offer the
alternative if there is one, and let the reviewer decide. Do not pad a
disagreement with softeners to make it feel gentler.

## Evidence

If a reviewer would reasonably want proof, the strongest form is short:

- "Repros on the attached test; it fails without the fix."
- "Verified: all three nodes now notify `oncallteam-mitra_training`."
- A link to the test run or paste.

Never a wall of captured output. The test plan is where evidence lives.

## Before and after

A real reply to "should we consider switching from `content_understanding` to
something else (maybe `mitra`?)", in three drafts. Note that the second draft
still failed review.

**Draft 1, over-produced:**
> Yes, and thank you, this was incoherent as written: a pipeline owned by
> `mitra_training` sitting in the `content_understanding` namespace.
>
> Moved to `mitra/demo_serving`, and the file with it, to
> `source/mitra/release/demo_serving.conveyor_config.cconf`.
>
> There is a closer precedent than the one I copied from. `mitra_grpo` is
> `CONVEYOR_ID = "mitra/mitra_grpo"` with `ONCALL = "mitra_training"`... I modelled
> on cu_core instead...
>
> ```
> conveyor_id: mitra/demo_serving
> ```
>
> One consequence worth naming for whoever grants it: the ACL grant after this
> lands is now against `CONVEYOR_ID:mitra/demo_serving`.

**Draft 2, still too long:**
> Agreed, moved to `mitra/demo_serving` and the file to `source/mitra/release/`.
> `mitra_grpo` was the precedent I should have used: same namespace, same oncall,
> same contbuild trigger. Note the post-land ACL grant is now against
> `CONVEYOR_ID:mitra/demo_serving`.

Draft 2 cut the headers, the praise opener and the output dump, and was still
rejected: the precedent sentence is self-narration and the ACL sentence is a
consequence aside. Trimming the obvious slop is not the same as answering the
question.

**Draft 3, right:**
> Agreed, moved to `mitra/demo_serving` and the file to `source/mitra/release/`.

---

**Over-produced:**
> **1 (`-h` in any position):** declining, with detail on the inline thread. A
> stricter check requires the wrapper to know which flags consume a value, which
> is a second copy of the parser grammar and the exact drift this diff removes...

**Fixed:**
> Declining: a stricter check means the wrapper knowing which flags take values,
> which is the parser grammar duplicated one layer up.

## Mechanics

- Reply on a thread: `meta phabricator.diff reply-comment -n D<n> -c <id> -m "..."`
- Top-level comment: `meta phabricator.diff comment -n D<n> -m "..."`
  (general/agent comments have no thread; `reply-comment` returns "not found")
- After a comment is addressed, resolve it:
  `meta phabricator.diff resolve-comments --number=D<n> --comment-id=<id>`
  Unresolved threads show up as an `Unresolved Comments` signal.
- Read the FULL comment list before replying (`comments -n D<n> --no-truncate`).
  Do not grep it for the automated reviewers: that filters out the humans.
