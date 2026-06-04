# Writer Spec Protocol

When writing a design spec, follow this structure. Every section is required unless marked optional. Fill each section from the resolved decisions included in your prompt.

---

## Document Structure

```
# [Feature Name] — Design Spec

## Context
What exists today, what's missing, why this work is needed.
2-3 sentences grounding the reader.

## Goals
Numbered list of objectives. Each goal is one sentence, starts with a bold keyword.
Example:
1. **Autonomous planning** — the skill runs until...
2. **Contextual auto-answering** — uses domain-tagged...

## Architecture
Diagram (ASCII art or description) showing how components fit together.
2-3 sentences explaining the flow.

## [Design Sections]
One section per major component or subsystem. This is the bulk of the spec.
Each section covers: what it does, how it works, config/schema if applicable.
Use code blocks for schemas, configs, and interface definitions.
Use tables for mappings and field descriptions.

## File Changes
Tables of new and modified files, grouped by component:
| File | Description |
|------|-------------|

## Verification
Numbered checklist. "This is done when..."
Each item is independently testable.

## Resolved Questions
Populated from the decision log included in your prompt. Each decision becomes one entry:
N. **[Question topic]:** → [Answer]. [Source/rationale if non-obvious.]

## Out of Scope
Bulleted list of what this explicitly does NOT include.
```

## Rules

- Use terms from CONTEXT.md exactly — don't introduce synonyms
- Every design decision from the decision log must appear in a design section
- Populate the Resolved Questions section from the full decision log
- No placeholders (TBD, TODO, "to be determined")
- No fuzzy language ("handle appropriately", "as needed")
- Code blocks for anything that has a concrete shape (schemas, configs, interfaces)
- Keep sections focused — if a section exceeds ~200 lines, it probably needs splitting
