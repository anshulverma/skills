# Final Cross-Cutting Review Checklist

You are doing a final review of ALL artifacts produced by auto-plan: spec, ADRs, implementation plan, and CONTEXT.md updates. All artifacts are included in your prompt below. Check for cross-artifact consistency.

## Checklist

1. **Spec ↔ plan consistency.** Every spec requirement maps to a plan task. Every plan task traces back to a spec requirement. List orphaned requirements and orphaned tasks.

2. **CONTEXT.md completeness.** Every new term introduced in the spec or plan is defined in CONTEXT.md. No term is used before it's defined.

3. **ADR consistency.** If ADRs were produced, do they contradict anything in the spec? Does the spec reference decisions documented in ADRs correctly?

4. **No unresolved markers.** Search all artifacts for: "UNRESOLVED," "TBD," "TODO," "to be determined." If found, this is expected only when --max-iterations was hit. Otherwise it's a failure.

5. **Term consistency across artifacts.** The same concept must use the same term everywhere. If the spec calls it "entity ref" but the plan calls it "entity reference," that's a bug.

6. **No dangling references.** No artifact references a concept, type, function, or file that isn't defined in another artifact. Every cross-reference must resolve.

## Response Format

```
### Result: PASS or FAIL

### Issues (if FAIL)
1. [checklist item number]: [artifact] [specific text] → [what's wrong] → [suggested fix]
2. ...
```
