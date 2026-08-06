# monk: scope

Repo mode's tree. Pointed at a repository rather than a diff, monk has no changed lines to root a
chain in, so something else has to decide what a review unit is, how many run, in what order, what
each one is guaranteed to be told, who owns a chain that crosses two of them, and what it means for
a run to stop half way. This file decides all of that.

This file is the normative owner of the four tree nouns (leaf group, node, unit, subtree), of the
unit filename and slug derivation, of artifact-kind detection, of the boundary-file rule and the
degenerate collapses, of the two-pass traversal, of the lowest-common-ancestor ownership rule that
replaces diff mode's stitch in repo mode, of the upward record and its summarization discipline, of
the ranking formula, of subtree-atomic budgeting and resume, and of the closed subtree-state
vocabulary. `SKILL.md` owns the invocations themselves and points here for what a resolved repo
invocation then does.

## What this file does not own

| Owned elsewhere | Owner |
|---|---|
| flag parsing and mutual exclusion for `--repo`, `--scope`, `--budget`, and `--since` | `SKILL.md`'s `## Input resolution (C1)` |
| the quality classes Q1 through Q8, the evidence bar, and the tier names the coverage blocks print | `references/QUALITY.md` |
| the four per-file coverage statuses, the concurrency cap, and diff mode's ownership and stitch rules | `references/FANOUT.md` |
| warrant grades, edge kinds, the terminal sets, the negation test, and the chain predicate | `references/METHOD.md` |
| manifest and ledger keys, cross-run matching, and the calibration window | `references/PERSISTENCE.md` |
| which tier a finding lands in, and the caps that evict from it | `SKILL.md` |

This file decides what gets reviewed and in what order. It never decides what counts as a finding.

## The four tree nouns

Each noun does four jobs at once: it is the budget count, the cap scope, the Must Fix tripwire
scope, and a ledger filename. An earlier draft used all four words without defining any of them.

| Noun | Definition |
|---|---|
| **leaf group** | 1 to 5 files of the same artifact kind in one directory, at most 1,500 lines total. A single file over 1,500 lines is its own leaf group and is never split |
| **node** | a directory that has **at least one subdirectory**, or whose own files form 2 or more leaf groups. A directory holding only files that form exactly one leaf group is **not** a node |
| **unit** | any leaf group **or** node that receives a review. Nodes and the root **are** units, they **do** consume budget, and each gets one ledger file. This is the count `--budget <n>` bounds, the scope the caps and the Must Fix tripwire apply to, and the `<unit>` in `reviews/repo-<slug>/<unit>.md` |
| **subtree** | a node plus everything beneath it. Any node at any depth may be a budget candidate, not only a top-level child. `N of M subtrees` counts **top-level children of the scope root**, since that is the number a reader can hold |

Both numbers in the leaf-group bound are monk's diff-mode constants reused rather than new ones
invented: 5 is the fan-out threshold in `references/FANOUT.md`'s `## Threshold and unit`, and 1,500
lines is the diff-inlining budget in `references/FANOUT.md`'s `## Execution [E-D10]`. Reusing them
keeps one story about how much one reasoner holds.

### Unit filenames and the slug

`<unit>` as a filename is the unit's scope-root-relative path with `/` replaced by `-`, so the
`monk/references` node becomes `monk-references.md`. Where one directory yields two leaf groups of
different artifact kinds, the kind is appended: `monk-references-code.md` and
`monk-references-docs.md`. A node and a collapsed leaf group never collide, because a collapsed
group **is** that directory's review and only one file is written. The mapping is deterministic and
reversible.

`<slug>` is the scope root's basename, lowercased, with non-alphanumerics collapsed to `-`, so
`~/workspace/skills` gives `skills`.

### Boundary files

**Boundary files** are the files sitting directly in a node's own directory: `README`, `__init__`,
`index`, entry points, and interface declarations. They are read **by the node** and are **not**
additionally a child leaf group, which prevents the double review the collapse rule exists to avoid.

Boundary files do **not** suppress nodehood, and getting this backwards deletes reviews rather than
merely misnaming them. `monk/` holds `SKILL.md` plus `references/`. An earlier draft made
`SKILL.md` a boundary file, which left `references/` as the single child, which collapsed `monk/`
under the one-group rule, which deleted the only review that reads a skill file against the
reference files it cites: exactly the review that finds a contradiction between two files and a
drifted duplicate of a normative table, neither of which is visible from either file alone. A
directory with **any** subdirectory is a node. `monk/` is reviewed as a boundary and reads
`SKILL.md` while doing it.

## Degenerate cases

| Shape | Rule |
|---|---|
| a directory whose files collapse into exactly one leaf group | **no separate node review**. That group's review **is** the directory's review. Without this a one-file directory is reviewed twice |
| a chain of single-child directories | collapses into **one** node. `a/b/c/d` with one child each is one node, not four |
| a flat directory exceeding the leaf bound | splits into several sized leaf groups, which become children of that directory's node. Grouping is **by declared intent where the directory states one, otherwise lexical**, so the split is deterministic and reproducible across runs rather than reshuffling on each one |
| a single file over 1,500 lines | its own leaf group, **never split**, per the existing prohibition on splitting one file across two agents. It gets prioritized passes over its symbols and a coverage note if it cannot finish |

## Artifact-kind detection

Resolved per **file**, by extension and content sniff, and resolved **before** grouping, so a leaf
group is same-kind by construction rather than by a kind inferred after the group exists. A
directory mixing the two kinds yields one leaf group per kind, both children of that directory's
node.

| Kind | Test | Handling |
|---|---|---|
| `code` | a source extension with a runtime | reviewed against the code terminal set |
| `document` | markdown, rst, or plain text that states rules, specs, or instructions | reviewed against the document terminal set |
| narrative markdown (a changelog, a blog post) | states nothing a reader is required to follow | `skipped-with-reason: not normative` |
| generated or vendored | header sniff and path convention, exactly as in diff mode | `skipped-with-reason`, no agent |

When the sniff is uncertain, **count the file and assign an agent**. A wasted review is cheaper than
a silent skip, which is the same trade diff mode already makes for a file wrongly sniffed as
generated.

## The two passes

### Pass 1: descend to declare intent

Reads **declared intent only**: `README`, `CLAUDE.md`, module docstrings, package metadata, skill
frontmatter, and directory names. It reads no code.

Each node inherits its ancestors' declared purpose. The output is an intent spine, one line per
node, which is what gives every leaf something to check itself against: rule 7, diff the code
against the author's own summary, mapped onto a repository as diff the code against its own
documentation. A node with no declared intent records `Intent: none stated` and inherits its nearest
ancestor's, marked as inherited.

Three properties of the descent are load-bearing:

- It covers the **whole tree**, not only budgeted subtrees, because an inherited purpose is what a leaf checks itself against and a budgeted subtree's own ancestors may be unbudgeted.
- It is **one orchestrator read**, not one agent per node.
- It therefore **does not consume budget**. It is cheap by construction: declared-intent files only, no code.

### Pass 2: ascend to review

Post-order. A node is reviewed only after every child has returned.

| Node kind | Reads | Owns |
|---|---|---|
| **leaf** (one file, or a sized group of same-kind files in one directory) | the files in full, plus any file a link needs | chains rooted in its own files |
| **internal** | every child's upward record, plus its own boundary files | **chains and Q findings rooted wholly in its own boundary files** (a boundary file is not a leaf group, so without this clause nothing owns them); chains spanning two or more children; the boundary evaluation, which may raise **any** of Q1 through Q8, not a subset; intent against implementation at this level; dedupe and promotion of children's findings |
| **root** | every top-level record | the whole-repo architecture review, plus unresolved open ends |

Siblings are independent, so each level is one parallel wave under the existing concurrency cap in
`references/FANOUT.md`'s `## Execution [E-D10]`. Levels run sequentially.

### Chain ownership: lowest common ancestor

> A chain is owned by the lowest node in the tree that contains every file the chain touches.

A chain inside one file is owned by that leaf. A chain across two files in one directory is owned by
that directory. A chain across two directories is owned by their common ancestor. The rule is
deterministic and total, and it costs O(depth) joins rather than O(pairs).

**This is the repo-mode rule, and it reverses a rule diff mode records as settled, so it says so.**
`references/FANOUT.md`'s `## Ownership: accountability, not aperture [E-D1]` assigns a chain to the
agent owning its **root file**, and
`references/FANOUT.md`'s `## Stitching: two distinct roles [E-D4]` completes a cross-file chain by
matching EXPORT and IMPORT pairs on symbol identity plus property. Both **stay in force for diff
mode**, unchanged, along with the stage-1 and stage-2 split. Repo mode substitutes the lowest node
rule for both, because a repository already has a tree and reading ownership off it beats matching
pairs heuristically.

Open ends still exist and still propagate. In repo mode they are resolved by the ancestor node
review rather than by a dispatched pair agent.

## The upward record

What a child hands its parent. It reuses the existing block-header style, so both modes parse the
same way.

```
### UNIT
path: <dir or file group> | kind: code|document | children: <N>

### CONTRACT
exposes: <what callers outside this unit may depend on>
depends: <what this unit needs from outside it>

### PURPOSE
<2-3 lines: what this unit is for, and whether that matches its declared intent>

### INVARIANTS
<facts about this subtree an ancestor needs, e.g. "every file here assumes the
 config was validated upstream">

### OPEN-ENDS
<the existing EXPORT/IMPORT schema, carried VERBATIM>

### FINDINGS
<closed, tiered proposals; ancestors dedupe and never re-derive>

### COVERAGE
<the existing four statuses: reviewed | skipped-with-reason | partial | unreviewed>
```

`INVARIANTS` is the layered-context mechanism: understanding flowing upward, not only findings.

### A separate schema, not an edit to the shared one

`SKILL.md`'s `### Response schema (parsing contract)` and `references/FANOUT.md`'s
`### Response schema (parsing contract)` carry a fenced block that is byte-identical in both files
by design, and is checked as such. The upward record does **not** touch it. It is an additional
schema, owned here under this heading and cited from elsewhere. Repo-mode leaf agents still emit the
existing `### COVERAGE`, `### DELTA`, `### CHAINS`, `### OPEN-ENDS`, `### UNPROVEN-FACTS`, and
`### ABANDONED` blocks unchanged; node agents additionally emit `### UNIT`, `### CONTRACT`,
`### PURPOSE`, and `### INVARIANTS`.

### The summarization discipline

Summarizing at every level loses information, and by the root a naive design is reading a summary of
a summary of a summary. That is the lens fan-out failure on a new axis: no single reasoner holds the
chain. The rule that prevents it:

> Summarize what closed. Carry what is open verbatim.

Read as one line: summarize what closed, carry what is open verbatim. Closed work compresses into
`PURPOSE`, `CONTRACT`, and `INVARIANTS`. `OPEN-ENDS` propagate unsummarized, because they are
precisely what an ancestor must reason about. `FINDINGS` propagate as closed records, so an ancestor
can dedupe without re-deriving.

**Aperture stays unlimited.** The upward record is a node's **guaranteed** context, never its
**permitted** context. A node may open any file in the repository, at any depth, inside or outside
its own subtree. Ownership decides who must report; it never limits reading, and repo mode does not
narrow that.

### An open end that leaves the declared scope

An open end whose consuming side lies outside the declared scope is not carried forever and is not
silently dropped. It is closed as an `Outside review scope` line, the tier
`references/QUALITY.md`'s `## Tier names` defines, which is capped by displacement and never counted
in the verdict.

## Ranking

Ranks **which subtree to review next**, not which flat unit, because budget is spent
subtree-atomically.

```
rank = churn x size x primitive-density
```

Each factor is normalised to 0-1 across the candidate set **before** multiplying, so no factor's raw
units dominate the product.

| Factor | Value |
|---|---|
| churn | commits touching the subtree in the last 12 months, from `git log --format= --name-only <path>`, divided by the maximum across candidates. A command, not a shipped script: monk stays markdown-only |
| size | subtree lines, divided by the maximum across candidates |
| primitive-density | the fraction of the subtree's files containing at least one primitive marker |

Primitive markers, per artifact kind:

| Kind | Class | Markers |
|---|---|---|
| code | concurrency | `thread`, `lock`, `async`, `spawn`, `dist.` |
| code | I/O | `open(`, `read`, `write`, `request`, `client` |
| code | auth | `token`, `acl`, `cred`, `permission` |
| code | persistence | `commit`, `save`, `checkpoint`, `flush` |
| code | numerics | `float`, `dtype`, `mean`, `sum` |
| document | normative language | `must`, `never`, `always`, `MUST` |
| document | tables | a markdown table |

Ties break on **shallowest depth**, then **lexical path**, so the ordering is total and reproducible
across runs.

## Budget and resume

Budget is spent **subtree-atomically**. monk selects the highest-ranked subtree that fits the
remaining budget and completes it, leaves through to that subtree's own root, before starting
another. The default is **25 units**, and `--budget <n>` overrides it.

A subtree larger than the entire budget is **skipped**, with a coverage row naming its size, and the
report suggests a `--scope` into it rather than starting a review it cannot finish.

The consequence is the reason for the choice: **every node review that exists is complete.** A
boundary review resting on partly-reviewed children is the least trustworthy output monk could
produce, and the Q1, Q3, and Q5 findings derived from one can be flatly wrong.

### The deferred root

The root review runs only when every top-level child is complete. Otherwise the report says
`root review deferred, N of M subtrees complete`.

A deferred root is the expected case, not an error, which creates a problem: an open end crossing
two subtrees has no owner until the root runs, and would be lost between runs. So **unresolved open
ends are persisted in the manifest and carried across runs**, and re-presented to the root review
when it eventually runs. Until then the report prints `open ends pending root review: N`, so a
deferred root is visible rather than silent. This is the repo-mode form of the existing rule that an
open end stays alive until it is matched, dispatched, or explicitly closed by an agent that read the
consuming side and found nothing.

### Resume

The inventory is built once per repository, persisted in the manifest, and re-checked against HEAD
on resume. A unit whose content hash changed **returns to the queue**, and its ancestors' node
reviews are **invalidated and requeued** with it, because a boundary review rests on its children
and a stale one asserts a boundary that no longer exists.

### Composing with `--since`

`--since <rev>` **intersects** `--scope`, budget is applied **after** the filtering, and resume
**re-filters rather than re-ranks**, so a resumed run does not reorder work it has already reported.
Exclusion lands at two different granularities, because subtree states and per-file statuses are
orthogonal:

| Excluded thing | Records as |
|---|---|
| a whole subtree | subtree state `skipped` |
| a file inside a reviewed unit | per-file status `skipped-with-reason: outside --since` |

## Subtree states

A closed vocabulary, owned here. It describes a whole subtree's **budget disposition**.

| State | Meaning |
|---|---|
| `complete` | every unit in the subtree was reviewed, leaves through to the subtree's own root |
| `deferred` | budget ran out before the subtree started. Still queued, and picked up by a later run |
| `skipped` | deliberately excluded: by `--scope`, by `--since`, or by being larger than the whole budget |

These three are **orthogonal** to the four per-file coverage statuses (`reviewed`,
`skipped-with-reason`, `partial`, `unreviewed`) that `references/FANOUT.md` owns and the
`### COVERAGE` block emits. One is about budget, the other about whether a file was read. The repo
report prints both in **separate blocks, never merged**: collapsing them would let a deliberate
stopping point read as a failure, or worse, let a failure read as a deliberate stopping point.

All three states print, so the denominator never silently shrinks. A bare `Clean` still requires
full coverage: an unbudgeted subtree forces the parenthesised form, exactly as an unreviewed file
does.

## Open calibration questions

These values are binding today. Each names what would change it.

- **The ranking formula `churn x size x primitive-density`, equally weighted after normalisation.**
  A heuristic, with no measurement behind the weighting, stated as a formula because a stated
  formula beats an implementer's guess. Revisit once a real repository run shows the ranking putting
  a low-value subtree first.
- **The primitive marker lists.** Literal substrings chosen for cheapness rather than precision, and
  biased toward Python-shaped code and markdown-shaped documents. They will under-count a language
  whose concurrency and I/O vocabulary differs. Extend the lists per language when a run visibly
  mis-ranks a subtree; do not replace the substring test with parsing, which needs a script and monk
  ships none.
- **The default budget of 25 units.** Invented, exactly as the existing per-unit cap of 3 is. Record
  budgeted units against total units per run: raise it if the common case is a run that cannot
  complete even one top-level subtree, lower it if runs routinely finish with budget unspent.
- **The leaf group bound of 5 files or 1,500 lines, whichever binds first.** Both are monk's
  diff-mode constants reused rather than new numbers, which is the justification for them and also
  the limit of it: nothing measures whether the amount one reasoner holds well is the same for a
  whole file as for a hunk. Revisit if leaf reviews start returning `partial`.
