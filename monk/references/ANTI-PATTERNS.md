# monk: anti-patterns

Four automated reviewers ran on the diff that motivated this skill and none of them held the
whole chain. This file quotes their prompts, because the instructions are the explanation. Each
reviewer behaves exactly as written; the misses are designed in, not accidents of sampling.

Every quote below is verbatim from the cited `path:line`, read out of fbsource. Prompts are
living files and will drift, so treat the line numbers as of this writing and re-read before
relying on a quote in an argument. Where a prompt carries an exception or a narrowing clause that
softens the quoted rule, the clause is named too: a file whose purpose is quoting other people is
worthless if it quotes them unfairly.

Each quote is followed by the monk rule it contradicts and where that rule lives. The rules are
numbered in `references/METHOD.md`, `## The seven rules`, and cited here by number only.

## Devmate: system state, app state, and author intent are out of bounds

`tools/devmate/configs/mcp_servers/code_review/reviewers/general_code_reviewer.md:79-80`:

```
practices and errors. Only detect problems with the code itself: do not consider
the system state, the app state, or the author's intent.
```

The shared system instructions say the same thing at greater length, and supply the reason.
`tools/devmate/configs/mcp_servers/code_review/common/prompts.system.instructions.general_reviewer.yaml:73-77`:

```
  - Do NOT review for system-level or app-level issues. You don't have the
    necessary context to review that effectively. Focus purely on the code change
    you are being asked to review, and nothing more. Don't guess whether the
    system state is ready or correct, or whether an app is initialized or not;
    assume that outside the code change, the system is ready and correct.
```

This contradicts rule 4, runtime and system state are in scope, which `METHOD.md` records as the
clearest measured delta against Devmate and ACR. The stated justification is a context claim: the
reviewer does not have the context, so it should not guess. monk's answer is not that guessing is
fine. It is that the context is obtainable by reading, and that a fact obtained by reading is not a
guess. Rule 4 also does not stand alone: `METHOD.md`'s warrant grades set what a runtime claim must
produce before it counts as a link at all, so an ungrounded assertion about production fails under
monk as surely as it does under this instruction. What monk refuses is the prior restraint.

Fairness note, and it matters for what this file is claiming: the Devmate general reviewer is not
told to drop uncertain findings. The same file at
`tools/devmate/configs/mcp_servers/code_review/reviewers/general_code_reviewer.md:82-84` says the
opposite:

```
Report every issue you find, including ones you are uncertain about or consider
low-severity. Do not filter for importance or confidence at this stage - a
separate verification step will do that. Your goal here is coverage: it is better
```

So Devmate's aperture is the restriction, and its filtering happens downstream. The two failures
are independent, and only the first one is Devmate's prompt.

## Devmate: a comment explaining a decision closes the question

Same shared instructions, `prompts.system.instructions.general_reviewer.yaml:79-82`:

```
  - Trust that intentional decisions made by the author of the code change are
    correct - for example, intentionally ignoring a lint error, evaluating logic,
    or using a specific framework, function, or API. If there's a comment
    explaining a code decision, do not flag an issue with that code.
```

This contradicts rule 6, a code comment is a hypothesis, not an alibi. `METHOD.md` records why
the rule exists: on the motivating diff the deadlock sat under a comment claiming it prevented
deadlock. Under the instruction above, that comment is the reason not to look.

The same file does carve out an exception at
`prompts.system.instructions.general_reviewer.yaml:83-88`, requiring an error-severity issue to be
flagged regardless of a comment or apparent intent, and giving the reason: the risk of missing a
SEV-causing issue outweighs the cost of a false positive. The carve-out is real, and it is the same
trade monk makes. The gap is that it applies only once the reviewer has already concluded the issue
is severe, and a chain whose severity is only visible at link five never gets classified that high
in the first place.

## ACR tier 1: the hunk aperture

`fbcode/claude-templates/components/plugins/acr/agents/acr-tier1-general.md:27` defines what the
agent is given:

```
The orchestrator pre-fetches a fat diff (hunks plus ±50 lines of surrounding context per hunk)
```

and `acr-tier1-general.md:34` defines what it may go and get for itself:

```
**Do NOT use Read/Grep/Glob** for file content verification when a COMMIT_HASH is provided
```

Both quotes carry qualifiers worth stating. Line 34 continues by scoping the ban: the reason given
is that those tools read the local working copy, which may differ from the not-yet-landed diff, and
the same line still permits Read/Grep/Glob for exploring unrelated code context such as a library
API. Lines 29-32 offer `sl cat -r {COMMIT_HASH} {file_path}` as the sanctioned fallback, explicitly
including the case where the agent needs code more than 50 lines away from any hunk. The aperture
is therefore a default with an escape hatch, not a wall.

It still contradicts rule 3, read whole files, both versions, including untouched dependencies. A
default that supplies hunks plus 50 lines, and that answers "verify this" with "do not use the
obvious tool," makes reading an untouched file the effortful path. The motivating chain turned on
`exceptions.py:47`, a file the diff never touched and that no hunk window would have contained.
Rule 3 exists because the proof is often in a file the diff never touches, and a default aperture
decides how often that file gets opened.

## ACR tier 1: the surrounding system is assumed correct

Same file, `acr-tier1-general.md:207`:

```
**Focus on the diff, not the surrounding system.** Your analysis is limited to the code changes presented. Evaluate what the code does, not what surrounding infrastructure might provide. Assume external dependencies, runtime configurations, and deployment environments are correctly established unless the diff itself reveals otherwise
```

Contradicts rule 4, the same way the Devmate instruction does, and pairs with the aperture above:
if the runtime configuration must be assumed correct and the config file is outside the hunk
window, the assumption is unfalsifiable by construction. monk's counterpart is the satisfiability
check in `METHOD.md`: the trigger conjunction is tested against configs, call sites, and code paths
that monk actually read, which is the same question answered by reading instead of by assumption.
That check also kills chains, and kills more of them than it saves.

## ACR tier 1: comments as design alibi

Same file, `acr-tier1-general.md:209`:

```
**Respect explicit design choices.** If the code includes comments explaining a decision, or if patterns suggest deliberate tradeoffs, trust that the author considered the implications.
```

Contradicts rule 6. The line continues by directing focus to objective correctness of the
implementation rather than to alternative architectural choices, which is a reasonable scope
limit and not the problem. The problem is the first half: the comment is treated as evidence about
the code's behavior, when it is only evidence about what the author believed.

## ACR pre-publish: exclude when uncertain

`fbcode/claude-templates/components/plugins/acr/agents/acr-pre-publish-reviewer.md:67`:

```
When uncertain, exclude the finding. Precision over recall.
```

and `acr-pre-publish-reviewer.md:199-200`:

```
- Every issue must have >70% confidence
- When uncertain, exclude. A clean report with 0 issues is valuable.
```

The second half of that last line is right, and monk agrees with it emphatically: a clean report is
a first-class outcome, not a failure. The disagreement is with the disposal of the uncertain
middle. Rule 5 in `METHOD.md` says never drop the mid-confidence band, demote it. Under exclusion,
a finding whose mechanism is fully readable but whose significance depends on one deployment fact
is indistinguishable from a finding that is simply wrong, and both vanish. monk keeps that finding
and changes its shape instead: it publishes as Human Judgment in the conditional form that
`METHOD.md`'s residual-unknown bound defines, carrying the one fact that would settle it and the
person who can answer that question. `SKILL.md` owns the tier lookup and the gates that keep that
tier from becoming a dumping ground.

## Deep code review: the numeric discard

`fbcode/claude-templates/components/commands/deep-code-review.md:413`:

```
Discard any finding with `final_confidence < 80`.
```

`final_confidence` is computed by the validation table at `deep-code-review.md:405-411`, which
adjusts a raw score by a validator confidence, applies an additive boost when CI corroborates, and
caps the result when a counter-argument was not considered. The arithmetic is careful. It is
applied to a number that no rubric defines, and the discard is unconditional.

Contradicts rule 5, and also the reason monk emits no confidence decimal at all in report output:
a reader can audit the claim "this link is READ, and here is the `file:line`," and cannot audit a
bare score produced by no stated rubric. `SKILL.md` states the no-confidence-decimal rule and its
single exception.

## Mitra diff review bot: a score with no rubric, then a hard filter

`fbcode/confucius/analects/mitra/diff_review_bot/tasks.py:130-136` asks for the score:

```
        For each finding, provide:
        - file path and line number
        - severity (critical, high, medium)
        - confidence score (0.0 to 1.0)
        - category (BUG, SEC, ARCH, SCOPE)
        - clear description of the issue
        - suggested fix if applicable
```

`fbcode/confucius/analects/mitra/diff_review_bot/functions.py:120-122` filters on it:

```
    # --- Step 1: Pre-filter by confidence and category ---
    # Only keep findings with confidence >= 0.8
    high_confidence = [f for f in all_findings if f.get("confidence", 0) >= 0.8]
```

Nothing between the ask and the filter tells the model what the number means. Two defects follow
from that, and both are worth naming because they are the mechanism by which the mid-confidence
band disappears rather than a stylistic complaint:

- The scales disagree. `tasks.py:124` states the bar in prose as `1. Provable bugs and security
  vulnerabilities (high confidence >= 80%)` while the filter compares against a 0.0-to-1.0 float.
- A missing field is silently a drop. `f.get("confidence", 0)` defaults an absent or unparsed score
  to zero, so a finding the model declined to score is discarded exactly like a finding it scored
  as worthless.

The same prompt agrees with monk about scope: `tasks.py:128` reads
`Do NOT flag style, naming, or convention issues.` That agreement is the point of the next section.
Everyone bans style findings. Style findings arrive anyway, under other names.

## The four load-bearing negatives

Four plausible explanations for monk's delta, all of them wrong. They are listed as negatives
because each one is a change a future maintainer could make while believing they were strengthening
the skill, and each one would spend effort where the measurement says there is nothing to gain.

**Not fan-out.** The competitors already fan out. The deep code review command dispatches parallel
agents, and ACR runs numbered tiers plus a separate validator and aggregator
(`fbcode/claude-templates/components/plugins/acr/agents/`). More reasoners was not the missing
ingredient, and the particular shape they fan out in is the injury: a perf agent plus a correctness
agent plus a security agent is precisely the arrangement that turns a five-link chain ending in a
cluster hang into a performance nit, because no single agent ever holds more than one link. That is
rule 1. monk does fan out, by file or subsystem only, which is rule 2, with the threshold and the
mechanics owned by `references/FANOUT.md`. Fan-out is a scaling device here, never the source of
the delta, and lens fan-out is banned at every level including inside an owner agent.

**Not adversarial verification.** A second model grading the first model's output is already
standard: ACR has a validator agent, and the deep code review command runs the confidence
arithmetic at `deep-code-review.md:405-411` on top of it. It did not recover the chain, and the
reason is structural rather than a tuning problem. A verifier inherits both the aperture and the
vocabulary of the finding it is handed. Asked whether a performance nit is real, it can answer yes
or no; it cannot answer "this is not a performance nit, it is link 1 of a deadlock," because
extending the chain is not the question it was given. Verification adjusts a label. monk's
analogue is not a verifier stage at the end but the per-link discipline during construction, the
negation test and the trigger satisfiability check in `references/METHOD.md`, plus escalation for
the facts that reading cannot settle.

**Not model class.** No model is strong enough to reason about bytes that are not in its context.
Behind a hunk-plus-50-lines aperture with file reads discouraged, every model class sees the same
window, and none of them sees `exceptions.py:47`. Reasoning strength is real and monk benefits from
it, but the design deliberately spends it on deciding what to read next and on grading warrants,
not on inferring what an unread file probably contains, because an inference about an unopened file
is not evidence under `METHOD.md`'s warrant grades. When a monk run underperforms, the first
question is what it failed to open, and the model it ran on is not on the list of first questions.

**Not team invariant rules.** ACR ships global rule catalogs and per-team rules as their own tiers
(`acr/rules/global/`, `acr-tier2-global-rules.md`, `acr-tier3-team-rules.md`). Rule catalogs are
good at what they do: known patterns, cheaply, uniformly, with a stable false-positive profile.
They are also complete by construction with respect to their own contents, which is why they cannot
be the answer here. What survives every existing reviewer is novel logic with no pattern to match,
and `SKILL.md`'s calibration section carries how little of it there is per diff. Adding rules
raises the floor on known defects and moves the residual not at all.

What is left after subtracting all four is aperture and whole-chain custody: read enough, and keep
every link of one causal chain inside one reasoner until it reaches a terminal or dies. Everything
else in this skill is machinery for doing those two things without drowning the user in output.

## `simplify`: the taxonomy is taken, the execution model is refused

One sourcing note before the quotes, because this section breaks the rule the preamble states.
`simplify` is a built-in Claude Code skill, not an fbsource file, so it has no `path:line` to cite.
Both quotes below are the prompt the skill emits, read out of the shipped binary at
`node_modules/@anthropic-ai/claude-code-linux-x64/claude`. That is a build artifact and not a
stable citation, so re-read before relying on the wording. The tool name in the second quote is
interpolated at render time; everything else is literal.

`simplify` states its own scope first:

```
You are improving the quality of the changed code, not hunting for bugs. Review
it for reuse, simplification, efficiency, and altitude issues, then fix what you
find.
```

and then its execution model:

```
Launch **4 independent review agents** via the Agent tool, all in a
single message so they run concurrently. Pass each agent the diff and one of
the four angles below.
```

The four angles are reuse, simplification, efficiency, and altitude. One agent per angle is a
**lens split**, and it is the same shape as the perf agent plus correctness agent plus security
agent named under **Not fan-out** above: the arrangement that turns a five-link chain into a
performance nit, because no single agent ever holds more than one link. That is rule 1, never fan
out by lens, and rule 1 admits no exception for a lens set that happens to be about quality rather
than about severity.

monk's position on this skill is deliberately split, and the split is the point of writing the
section down. The **taxonomy is taken**: all four angles survive the fold into `QUALITY.md`'s
Q1-Q8, and its `## Where these came from` table is the row-by-row proof that nothing was dropped.
The **execution model is rejected**, in full, including inside an owner agent. A maintainer who
reads both skills will see monk carrying `simplify`'s vocabulary while running none of its
structure, and the available misreading is that monk is an unfinished port. It is not. The
divergence is the design.

In this file's fair-quoting tradition: `simplify` is not wrong for what it is, and the lens split
costs it nothing. It says plainly that it is not hunting for bugs, and it applies the fixes rather
than reporting them. Its findings are single-site by construction, so there is no chain to sever
and nothing an agent boundary can cut in half. Four angles in parallel is the right shape for that
job. The split is fatal only for chain construction, which is monk's whole job and is precisely
what `simplify` disclaims.

The direction of the pressure is worth naming too. `simplify` is a shipped, well-known skill with
a visibly simpler structure, so "why does monk not just do what `simplify` does" is the easy
question and "because rule 1" is the answer, every time.

## Style laundering

Style, naming, formatting, and convention are not monk's scope. Lint owns them, and as
`tasks.py:128` shows, every competing reviewer bans them too. Banning them is not the hard part.

The hard part is that a style objection with nowhere to go gets renamed. "Maintainability risk" and
"readability concern" are the two common disguises, and the rule is that a relabelled style
objection is the same objection and is equally out of scope. It does not become in scope by
acquiring a more serious-sounding category, and it does not become a finding by being attached to a
tier that admits uncertainty.

This matters most at the tier that carries conditional findings, which is where a laundered
objection is easiest to hide, so the ban is enforced there: relabelling is banned by gate 4 of
`SKILL.md`'s Human Judgment gates. `SKILL.md` states the rule; this file only records why it exists
and what it is defending against.

## Agreement between agents is not corroboration

Two owner agents reaching the same conclusion feels like independent confirmation and is not. The
normative rule, with its reasoning and its consequences for dedup, is owned by
`references/FANOUT.md`'s dedup section. It appears in this file because treating agreement as
evidence is an anti-pattern with a specific victim: it is the mechanism by which correlated
agents inflate a conditional finding into a Must Fix, which attacks the calibration the skill
ships to defend and pushes the false positive rate off its measured baseline.

## The reversal to watch for

Two of them, and the second arrived with the Improvements tier.

### First: a threshold on conditional findings

The design decision most likely to be reversed by a well-meaning future maintainer is the one that
keeps conditional findings visible. Output feels noisy, and the obvious remedies are a minimum
confidence threshold or a filter that hides anything written conditionally.

Do not add either. Both reproduce the failure measured across all four reviewers above. On
D114284934 both author-confirmed findings had fully readable mechanisms whose significance turned
on deployment facts, which is exactly the profile a mid-confidence score encodes and exactly what
every threshold in this file discards. Dropping that material drops the findings monk exists to
produce, which is why rule 5 in `METHOD.md` says demote rather than drop.

Noise control is already built, and it is built out of parts that a reader can audit: the reporting
floor, the tier caps enforced by displacement, the residual-unknown bound, and trigger
satisfiability, all of which kill chains for a stated reason that gets recorded. Those are the
knobs. A confidence filter is not one of them, and neither is suppressing the conditional form.

### Second: relaxing the Q evidence bar

The **evidence bar** on quality findings, owned by `QUALITY.md`'s `## The evidence bar`, is the
only thing standing between the Improvements tier and the dumping ground the rest of this file
describes. It admits three forms and nothing else: a present inconsistency, a real past change
that paid the cost cited by commit hash, or a checkable absence stated with how the absence was
established. A prediction is not one of them and a preference is not one of them.

Everything about relaxing it will feel like an improvement at the moment someone does it. The bar
is one paragraph, so it is a one-line change. It is stricter than either source skill, so it will
look like an unforced restriction rather than a defended one. It visibly kills useful-sounding
candidates, and the report even lists them one line each under `Q candidates dropped`, so the cost
of the bar is on screen every run while the benefit never is. And the relaxation has a reasonable
name ready to hand: "let a well-argued observation in without a citation."

That is the whole failure mode. Every "this would be cleaner" is well argued, because arguing is
free when nothing has to be cited. Drop the bar and the tier fills with them, silently, one
plausible entry at a time, and the Improvements section becomes the place a style objection goes
once `SKILL.md`'s gate 4 has thrown it out of Human Judgment. The anti-laundering gate cannot save
it either: laundering is about relabelling, and a candidate that clears no evidence form was never
mislabelled, it was simply never evidence.

The bar is not the noise control for this tier, and confusing the two is how it gets traded away.
Noise control is the per-unit and global caps enforced by displacement and the Q severity order
that decides what displaces what. The bar is the admission test. Tighten the caps if the tier is
too long. Leave the bar alone.
