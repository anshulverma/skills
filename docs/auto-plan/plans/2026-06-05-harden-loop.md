# auto-plan Hardening Meta-Loop (`--harden`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an opt-in `--harden` meta-loop to the `auto-plan` skill that re-examines generated
artifacts across fresh-context passes until a numeric instability score converges to 0.

**Architecture:** Three new prompt-fragment files define the Hardening Pass agent, its response
contract, and the convergence judge. `SKILL.md` gains a Phase 5 orchestrator section that loops:
snapshot → pass agent → apply edits → judge → score. State, report, and docs are extended.
Everything is Markdown; the orchestrator is the running `auto-plan` session.

**Tech Stack:** Markdown prose (skill fragments). No compiled code, no build. Best-effort PNG
rendering via `python3`+matplotlib or `gnuplot` at runtime.

**Test commands:** This skill has no code test suite (per `CLAUDE.md`). The verification analog
is grep/read assertions over the Markdown contracts:
- Run a single check: `grep -n "<exact string>" <file>`
- Run the full suite: the Task 8 checklist below (each line is a copy-pasteable `grep`/`test`).

Both the repo source (`auto-plan/`) and the deployed symlink (`~/.claude/skills/auto-plan/`) point
at the same files, so edits take effect immediately — no deploy step.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `auto-plan/HARDENING-PASS-PROTOCOL.md` | Pass agent playbook (review-and-patch, material-only, gating). |
| `auto-plan/HARDENING-PASS-RESPONSE-TEMPLATE.md` | Pass agent's 7-header response contract. |
| `auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md` | Judge rubric + CONVERGED/NOT CONVERGED format. |
| `auto-plan/SKILL.md` | Phase 5 loop, flags, collection logic, state/report/metric docs. |
| `CLAUDE.md` | Fragment architecture table + two new parsing contracts. |
| `README.md` | One paragraph on `--harden`. |

Build the three fragments first (they are referenced by SKILL.md), then SKILL.md, then CLAUDE.md
and README, then the cross-file verification.

---

## Task 1: HARDENING-PASS-RESPONSE-TEMPLATE.md (the contract)

**Files:**
- Create: `/home/anshul/workspace/skills/auto-plan/HARDENING-PASS-RESPONSE-TEMPLATE.md`

Build the response contract first — SKILL.md's collection logic and Task 2's protocol both
depend on these exact headers.

- [ ] **Step 1: Write the verification check (expect failure)**
Run: `test -f /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-RESPONSE-TEMPLATE.md && grep -c "^### " /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-RESPONSE-TEMPLATE.md`
Expected now: `No such file or directory` (file absent).

- [ ] **Step 2: Create the file** with exactly these seven `### ` headers, in order, matching the
spec's contract: `Edits`, `Decisions Changed`, `Gaps Filled`, `Unresolved Resolved`,
`ADR Candidates`, `Bubble-Up Questions`, `Material Change Assessment`. Under each header include
the one-line bullet format from the spec's "HARDENING-PASS-RESPONSE-TEMPLATE.md (contract)" block
(e.g. `Edits` → `- [artifact: spec|adr-NNNN|plan|context] | [section/anchor] | [full replacement body] | Why: [reason]`).
Open with: "Structure your response with these exact headers. The orchestrator's Phase 5
collection logic reads these sections. Missing sections are treated as empty."

- [ ] **Step 3: Run the check to verify it passes**
Run: `grep -c "^### " /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-RESPONSE-TEMPLATE.md`
Expected: `7`

- [ ] **Step 4: Verify header names exactly**
Run: `grep -n "^### \(Edits\|Decisions Changed\|Gaps Filled\|Unresolved Resolved\|ADR Candidates\|Bubble-Up Questions\|Material Change Assessment\)$" /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-RESPONSE-TEMPLATE.md | wc -l`
Expected: `7`

- [ ] **Step 5: Commit**
Run: `cd /home/anshul/workspace/skills && git add auto-plan/HARDENING-PASS-RESPONSE-TEMPLATE.md && git commit -m "feat(auto-plan): add Hardening Pass response template (orchestrator contract)"`

---

## Task 2: HARDENING-PASS-PROTOCOL.md (pass agent playbook)

**Files:**
- Create: `/home/anshul/workspace/skills/auto-plan/HARDENING-PASS-PROTOCOL.md`

- [ ] **Step 1: Write the verification check (expect failure)**
Run: `grep -l "material-only" /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-PROTOCOL.md`
Expected now: `No such file or directory`.

- [ ] **Step 2: Create the file.** Required content, each as its own subsection:
  - **Your Job:** harden the full artifact set in one cleared context; review-and-patch, not
    re-plan. Read all artifacts + the decision log; propose edits; return them — never write to
    disk.
  - **Material-only rule:** propose an edit ONLY if it is a Material change (adds/removes/alters a
    decision, scope, interface, edge case, UNRESOLVED marker, ADR, or numeric threshold).
    Standalone minor edits (wording/format) are FORBIDDEN. State that this is what guarantees
    convergence.
  - **Edit format:** return full-file replacement bodies for any artifact touched.
  - **Confidence gating:** resolve a gap yourself only at/above the run's `--confidence-threshold`;
    otherwise record a Bubble-Up Question with a recommendation and leave the gap.
  - **Do NOT:** re-invoke auto-plan; spawn sub-agents; explore the codebase (use Files Needed via
    Bubble-Up); edit against a settled decision (flag `conflict-with-settled: dNNN` instead).
  - **Respond using HARDENING-PASS-RESPONSE-TEMPLATE.md** (name it explicitly).

- [ ] **Step 3: Run the checks to verify they pass**
Run: `grep -c "material" /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-PROTOCOL.md`
Expected: a number `>= 3`.
Run: `grep -n "spawn\|sub-agent\|re-invoke" /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-PROTOCOL.md`
Expected: at least one line under the "Do NOT" subsection forbidding spawning/re-invocation.

- [ ] **Step 4: Verify the template is referenced by name**
Run: `grep -c "HARDENING-PASS-RESPONSE-TEMPLATE.md" /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-PROTOCOL.md`
Expected: `>= 1`

- [ ] **Step 5: Commit**
Run: `cd /home/anshul/workspace/skills && git add auto-plan/HARDENING-PASS-PROTOCOL.md && git commit -m "feat(auto-plan): add Hardening Pass agent protocol"`

---

## Task 3: CONVERGENCE-JUDGE-CHECKLIST.md (judge rubric + format)

**Files:**
- Create: `/home/anshul/workspace/skills/auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md`

- [ ] **Step 1: Write the verification check (expect failure)**
Run: `grep -n "CONVERGED" /home/anshul/workspace/skills/auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md`
Expected now: `No such file or directory`.

- [ ] **Step 2: Create the file.** Required content:
  - **Your Job:** independently diff the pass-(N-1) snapshot against the current artifacts;
    classify each change material vs minor; the pass agent's self-report is a cross-check only.
  - **Material rubric** (verbatim list from the spec's Convergence Judge section).
  - **Minor rubric** (verbatim list from the spec).
  - **Conservative bias:** when ambiguous, classify as material.
  - **Response Format** block with exactly these headers: `### Verdict: CONVERGED or NOT CONVERGED`,
    `### Changes` (a markdown table `| # | Artifact | Change summary | Classification: material/minor | Why |`),
    `### Open Gaps`, `### Rationale`.

- [ ] **Step 3: Run the checks to verify they pass**
Run: `grep -c "^### \(Verdict\|Changes\|Open Gaps\|Rationale\)" /home/anshul/workspace/skills/auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md`
Expected: `4`
Run: `grep -c "Conservative bias\|conservative bias" /home/anshul/workspace/skills/auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md`
Expected: `>= 1`

- [ ] **Step 4: Commit**
Run: `cd /home/anshul/workspace/skills && git add auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md && git commit -m "feat(auto-plan): add convergence judge checklist"`

---

## Task 4: SKILL.md — flags and Phase matrix

**Files:**
- Modify: `/home/anshul/workspace/skills/auto-plan/SKILL.md`

- [ ] **Step 1: Write the verification check (expect failure)**
Run: `grep -c "\-\-harden" /home/anshul/workspace/skills/auto-plan/SKILL.md`
Expected now: `0`

- [ ] **Step 2: Edit the Configuration flag table.** Add three rows after `--redo`:
  - `| \`--harden\` | off | Run the hardening meta-loop: re-examine artifacts across fresh-context passes until convergence. |`
  - `| \`--max-passes\` | \`3\` | Maximum hardening passes (distinct from \`--max-iterations\`). |`
  - `| \`--unattended\` | off | Suppress user prompts; bubble-up questions degrade to UNRESOLVED. |`

- [ ] **Step 3: Edit the Phase matrix table.** Add a row:
  `| \`--harden\` | 0 → … → 4, then Phase 5 loop | artifacts + convergence CSV/PNG + report |`

- [ ] **Step 4: Run the checks to verify they pass**
Run: `grep -c "\-\-harden\|\-\-max-passes\|\-\-unattended" /home/anshul/workspace/skills/auto-plan/SKILL.md`
Expected: `>= 4` (three flag rows + matrix row).

- [ ] **Step 5: Commit**
Run: `cd /home/anshul/workspace/skills && git add auto-plan/SKILL.md && git commit -m "feat(auto-plan): document --harden flags and phase matrix row"`

---

## Task 5: SKILL.md — Phase 5 section (loop + collection logic)

**Files:**
- Modify: `/home/anshul/workspace/skills/auto-plan/SKILL.md`

Add a "## Phase 5: Hardening Meta-Loop" section after Phase 4 and before "--redo Support".

- [ ] **Step 1: Write the verification check (expect failure)**
Run: `grep -c "Phase 5: Hardening Meta-Loop" /home/anshul/workspace/skills/auto-plan/SKILL.md`
Expected now: `0`

- [ ] **Step 2: Add the section** containing, verbatim from the design spec:
  - The loop pseudocode (the Phase 5 block: snapshot → pass agent → bubble-up handling → apply →
    judge → score → stop checks).
  - The `converged()` definition (0 material + 0 gaps + 0 UNRESOLVED + 0 pending).
  - The Hardening Pass agent dispatch (inputs list; `model: "opus"`; reads
    `HARDENING-PASS-PROTOCOL.md` + `HARDENING-PASS-RESPONSE-TEMPLATE.md`).
  - The **Pass-result collection logic** naming all seven response headers
    (`Edits`, `Decisions Changed`, `Gaps Filled`, `Unresolved Resolved`, `ADR Candidates`,
    `Bubble-Up Questions`, `Material Change Assessment`).
  - The Convergence judge dispatch (reads `CONVERGENCE-JUDGE-CHECKLIST.md`; `model: "opus"`;
    naming the four judge headers `Verdict`/`Changes`/`Open Gaps`/`Rationale`).
  - The Escalation/bubble-up handling (record-and-defer; confidence-gating table; unattended
    degradation; dedup; contradiction → `--redo` cascade).
  - The Termination table (converged / max_passes / oscillation / hard failure).
  - The instability-score formula and the convergence CSV/PNG outputs (matplotlib → gnuplot →
    ASCII fallback).

- [ ] **Step 3: Run the contract checks to verify they pass**
Run: `for h in Edits "Decisions Changed" "Gaps Filled" "Unresolved Resolved" "ADR Candidates" "Bubble-Up Questions" "Material Change Assessment"; do grep -q "$h" /home/anshul/workspace/skills/auto-plan/SKILL.md && echo "ok:$h" || echo "MISSING:$h"; done`
Expected: seven `ok:` lines, zero `MISSING:`.
Run: `grep -c "instability_score = material_changes + open_gaps + pending_questions + unresolved_markers" /home/anshul/workspace/skills/auto-plan/SKILL.md`
Expected: `1` (formula matches ADR 0006 / the judge checklist exactly).

- [ ] **Step 4: Commit**
Run: `cd /home/anshul/workspace/skills && git add auto-plan/SKILL.md && git commit -m "feat(auto-plan): add Phase 5 hardening meta-loop and collection logic"`

---

## Task 6: SKILL.md — state schema, resume, and report extensions

**Files:**
- Modify: `/home/anshul/workspace/skills/auto-plan/SKILL.md`

- [ ] **Step 1: Write the verification check (expect failure)**
Run: `grep -c "convergence_status" /home/anshul/workspace/skills/auto-plan/SKILL.md`
Expected now: `0`

- [ ] **Step 2: Extend the State File section** with the `harden` object (verbatim JSON from the
spec's State Schema Extension), the two-phase `running`→`complete` write rule, and the snapshot
layout/retention/frozen-date rules. Extend the **--resume Support** section with the
convergence_status / current_pass re-entry logic (running entry → restore from snapshot → re-run
the pass). Add a note to **--redo Support** that `--redo` is independent of the harden loop and
creates no snapshots.

- [ ] **Step 3: Extend the Planning Report section** with a `## Hardening Passes` table
(`| Pass | Material? | Gaps Filled | Questions Bubbled Up | Verdict Rationale | Snapshot |`), an
embedded `![convergence](...-convergence.png)`, and `Hardening passes: N` in Execution Stats.
Add the convergence CSV and PNG to the Output File Layout block.

- [ ] **Step 4: Run the checks to verify they pass**
Run: `grep -c "convergence_status\|snapshots/pass-\|Hardening Passes\|convergence.csv\|convergence.png" /home/anshul/workspace/skills/auto-plan/SKILL.md`
Expected: `>= 5`.

- [ ] **Step 5: Commit**
Run: `cd /home/anshul/workspace/skills && git add auto-plan/SKILL.md && git commit -m "feat(auto-plan): extend state schema, resume, and report for hardening"`

---

## Task 7: CLAUDE.md and README.md

**Files:**
- Modify: `/home/anshul/workspace/skills/CLAUDE.md`
- Modify: `/home/anshul/workspace/skills/README.md`

- [ ] **Step 1: Write the verification check (expect failure)**
Run: `grep -c "HARDENING-PASS-PROTOCOL" /home/anshul/workspace/skills/CLAUDE.md`
Expected now: `0`

- [ ] **Step 2: Edit CLAUDE.md.** Add three rows to the fragment architecture table
(`HARDENING-PASS-PROTOCOL.md`, `HARDENING-PASS-RESPONSE-TEMPLATE.md`, `CONVERGENCE-JUDGE-CHECKLIST.md`)
with their "Pasted into" column (Hardening Pass agent / Hardening Pass agent / Convergence judge).
In the "Consequences when editing" list, add that the `HARDENING-PASS-RESPONSE-TEMPLATE.md`
headers ↔ SKILL.md Phase 5 collection logic is a contract, and likewise the
`CONVERGENCE-JUDGE-CHECKLIST.md` headers ↔ judge-collection logic.

- [ ] **Step 3: Edit README.md.** Add one paragraph: `--harden` re-runs the whole flow across
fresh-context passes, filling gaps and hardening the plan until a numeric instability score
converges to 0, emitting a convergence chart with the report.

- [ ] **Step 4: Run the checks to verify they pass**
Run: `grep -c "HARDENING-PASS-PROTOCOL\|HARDENING-PASS-RESPONSE-TEMPLATE\|CONVERGENCE-JUDGE-CHECKLIST" /home/anshul/workspace/skills/CLAUDE.md`
Expected: `>= 3`
Run: `grep -c "harden" /home/anshul/workspace/skills/README.md`
Expected: `>= 1`

- [ ] **Step 5: Commit**
Run: `cd /home/anshul/workspace/skills && git add CLAUDE.md README.md && git commit -m "docs: document --harden fragments and capability"`

---

## Task 8: Cross-file contract verification

**Files:**
- Test: (no new file) — a final verification sweep over all edited files.

- [ ] **Step 1: Verify the response-template ↔ collection-logic contract** — every Pass header in
the template also appears in SKILL.md:
Run: `for h in Edits "Decisions Changed" "Gaps Filled" "Unresolved Resolved" "ADR Candidates" "Bubble-Up Questions" "Material Change Assessment"; do t=$(grep -c "$h" /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-RESPONSE-TEMPLATE.md); s=$(grep -c "$h" /home/anshul/workspace/skills/auto-plan/SKILL.md); [ "$t" -ge 1 ] && [ "$s" -ge 1 ] && echo "ok:$h" || echo "BROKEN:$h"; done`
Expected: seven `ok:` lines.

- [ ] **Step 2: Verify the judge ↔ collection-logic contract:**
Run: `for h in Verdict Changes "Open Gaps" Rationale; do j=$(grep -c "$h" /home/anshul/workspace/skills/auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md); s=$(grep -c "$h" /home/anshul/workspace/skills/auto-plan/SKILL.md); [ "$j" -ge 1 ] && [ "$s" -ge 1 ] && echo "ok:$h" || echo "BROKEN:$h"; done`
Expected: four `ok:` lines.

- [ ] **Step 3: Verify the instability-score formula is identical across the three files.** Use
`-ho` (only-matching) so the test compares the formula substring itself, not the surrounding
markdown — the formula legitimately sits in a fenced code block in SKILL.md but inline-code in the
judge checklist and ADR 0006:
Run: `grep -rho "instability_score = material_changes + open_gaps + pending_questions + unresolved_markers" /home/anshul/workspace/skills/auto-plan/SKILL.md /home/anshul/workspace/skills/auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md /home/anshul/workspace/skills/docs/adr/0006-instability-score-metric.md | sort -u | wc -l`
Expected: `1` (one canonical formula substring).
Run: `grep -rl "instability_score = material_changes + open_gaps + pending_questions + unresolved_markers" /home/anshul/workspace/skills/auto-plan/SKILL.md /home/anshul/workspace/skills/auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md /home/anshul/workspace/skills/docs/adr/0006-instability-score-metric.md | wc -l`
Expected: `3` (present in all three files).

- [ ] **Step 4: Verify no placeholders leaked into the fragments:**
Run: `grep -rn "TBD\|TODO\|FIXME\|to be determined\|placeholder" /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-PROTOCOL.md /home/anshul/workspace/skills/auto-plan/HARDENING-PASS-RESPONSE-TEMPLATE.md /home/anshul/workspace/skills/auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md`
Expected: no output (exit 1).

- [ ] **Step 5: Verify the deployed symlink sees the new fragments:**
Run: `ls /home/anshul/.claude/skills/auto-plan/HARDENING-PASS-PROTOCOL.md /home/anshul/.claude/skills/auto-plan/HARDENING-PASS-RESPONSE-TEMPLATE.md /home/anshul/.claude/skills/auto-plan/CONVERGENCE-JUDGE-CHECKLIST.md`
Expected: all three paths listed (no "No such file").

- [ ] **Step 6: Commit the verified state (if any fixups were needed):**
Run: `cd /home/anshul/workspace/skills && git add -A && git commit -m "test(auto-plan): verify --harden cross-file contracts" --allow-empty`
