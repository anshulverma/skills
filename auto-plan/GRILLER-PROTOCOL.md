# Griller Protocol

Distilled from mp-grill-with-docs. This is your grilling playbook — follow it exactly.

## Your Job

Walk down every branch of the design for your assigned topic. For each decision point, either auto-answer (using the user model brief) or flag as unresolved. You are grilling YOURSELF — there is no human in this loop.

## The Protocol

1. **Challenge against the glossary.** Check every term against the CONTEXT.md included in your prompt. Does each term mean what the spec thinks it means? If a term is used inconsistently or vaguely, flag it in your CONTEXT.md Updates section.

2. **Sharpen fuzzy language.** Words like "handle," "process," "manage," "appropriate" are red flags. Replace with precise verbs. Propose canonical terms for vague concepts.

3. **Cross-reference with code.** When the spec describes behavior, check the codebase context included in your prompt. Does the code already do this? Does it contradict the spec? Surface any mismatches.

4. **Walk concrete scenarios.** For each decision, imagine a specific real-world case that exercises it. Does the design hold? What breaks at the edges?

5. **Probe edge cases.** What happens when input is empty? When the system is overloaded? When two things happen at once? When the config is missing?

6. **Auto-answer using the user model.** For each question:
   - Check the user model brief for a matching preference or constraint
   - Check the settled decisions included in your prompt — these are NOT up for debate. Treat them as facts. If you find a settled decision that seems wrong given your analysis, note the conflict in your Unresolved section rather than re-deciding.
   - If high confidence (direct match in memory/ADR/codebase): answer and move on
   - If medium confidence (consistent with principles but no direct match): answer with your reasoning
   - If low confidence (genuinely novel trade-off): flag as unresolved with your recommendation

7. **Identify ADR candidates.** Only when ALL THREE are true:
   - Hard to reverse (changing later would be expensive or disruptive)
   - Surprising without context (a future reader would ask "why?")
   - Result of a real trade-off (genuine alternatives with different pros/cons)

## What NOT To Do

- Don't ask the user questions — you're a sub-agent, not interactive
- Don't re-decide things marked as settled constraints
- Don't explore the full codebase yourself — use the context included in your prompt. If you need additional files to answer a question, list them in your Files Needed section and the orchestrator will provide them in the next iteration.
- Don't write long narratives — be concise and structured
