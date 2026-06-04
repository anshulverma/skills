# Spec Review Checklist

You are reviewing a design spec produced by a Writer sub-agent. Check each item below. Report any failures with the specific text that violates the rule.

## Checklist

1. **Decision coverage.** Every resolved decision from the grilling sessions is reflected in the spec. Cross-reference the decision log included in your prompt below. List any decisions not found in the spec.

2. **No internal contradictions.** Read each section and check: does any statement contradict another section? Pay special attention to schemas, interfaces, and behavioral descriptions that appear in multiple places.

3. **No fuzzy language.** Search for: "handle," "process," "manage," "appropriate," "as needed," "etc.," "and so on," "relevant," "properly." Each is a red flag. Propose a precise replacement.

4. **Scope match.** Does the spec cover exactly what was agreed during grilling — no more, no less? Flag any scope creep (features not discussed) or missing pieces (discussed but not in spec).

5. **CONTEXT.md alignment.** Every term used in the spec must match CONTEXT.md exactly. Flag any synonyms, variant spellings, or terms used inconsistently.

6. **No placeholders.** Search for: "TBD," "TODO," "to be determined," "fill in," "implement later," "[...]," "placeholder." Each is a failure.

## Response Format

```
### Result: PASS or FAIL

### Issues (if FAIL)
1. [checklist item number]: [specific text that fails] → [what's wrong] → [suggested fix]
2. ...
```
