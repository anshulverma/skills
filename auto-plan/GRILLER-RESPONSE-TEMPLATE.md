# Griller Response Template

Structure your response with these exact headers. The orchestrator reads these sections to collect your results. Missing sections are treated as empty.

---

### Decisions

For each question you answered:

- [Question]: [Answer] | Confidence: high/medium/low | Source: [memory/ADR/codebase/principle/best-judgment]

Example:
- Canonical ID format: UUID4 | Confidence: high | Source: ADR 0009 + user preference for "do it now, avoid future migrations"
- Error retry strategy: 3x with exponential backoff | Confidence: medium | Source: consistent with existing adapter error isolation pattern in codebase

### Unresolved

For each question you couldn't answer confidently:

- [Question]: Recommended: [your best answer] | Confidence: low | Why uncertain: [what's missing — no signal in user model, genuinely novel trade-off, conflicting signals]

Example:
- Calendar event dedup strategy: Recommended: hash meaningful fields (title, time, location) | Confidence: low | Why uncertain: two valid approaches (hash vs etag), no user preference signal, both have different failure modes

### ADR Candidates

Only include if ALL THREE criteria are met: hard to reverse + surprising without context + result of a real trade-off.

- Title: [short title] | Context: [1 sentence] | Decision: [what was decided] | Alternatives: [what was rejected and why]

### CONTEXT.md Updates

New terms or sharpened definitions:

- **Term**: definition. _Avoid_: [synonyms to avoid]

### New Branches

Sub-topics discovered during grilling that need their own deep-dive:

- [Topic] — [why this needs separate exploration, what questions it raises]

### Files Needed

Files you need to see to answer questions in the Unresolved section. The orchestrator will fetch these and re-dispatch you with the additional context.

- [file path or search query] — needed to answer: [which question from Unresolved]
