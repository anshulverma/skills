# Writer Plan Protocol

Distilled from the writing-plans skill. Follow this format exactly when producing an implementation plan.

## Plan Header

Every plan starts with:

```
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** [One sentence]

**Architecture:** [2-3 sentences]

**Tech Stack:** [Key technologies]

**Test commands:**
- [How to run tests]
- [How to run a single test]

---
```

## File Structure

Before tasks, map out which files will be created or modified. Each file gets one clear responsibility.

## Task Format

```
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.ext`
- Modify: `exact/path/to/existing.ext`
- Test: `tests/exact/path/to/test.ext`

- [ ] **Step 1: Write the failing test**
[complete test code]

- [ ] **Step 2: Run test to verify it fails**
Run: [exact command]
Expected: [exact failure message]

- [ ] **Step 3: Write minimal implementation**
[complete implementation code]

- [ ] **Step 4: Run test to verify it passes**
Run: [exact command]
Expected: PASS

- [ ] **Step 5: Commit**
[exact commit command with message]
```

## Rules

- **TDD always** — write the test first, watch it fail, then implement
- **Bite-sized steps** — each step is one action (2-5 minutes)
- **No placeholders** — every step has complete code, exact commands, expected output
- **No "similar to Task N"** — repeat the code; the engineer may read tasks out of order
- **Exact file paths** — never use relative or ambiguous paths
- **Frequent commits** — commit after each task (not each step)
- **DRY, YAGNI** — don't add abstractions or features beyond what the spec requires
