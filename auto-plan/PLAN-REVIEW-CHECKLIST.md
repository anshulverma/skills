# Plan Review Checklist

You are reviewing an implementation plan produced by a Writer sub-agent. Check each item below against the design spec included in your prompt below.

## Checklist

1. **Spec coverage.** Every requirement in the spec maps to at least one task in the plan. Skim each spec section — can you point to the task that implements it? List any gaps.

2. **No placeholders.** Search for: "TBD," "TODO," "similar to Task N," "add appropriate," "handle edge cases," "fill in details," "implement later." Each is a failure. Every step must have complete code or exact commands.

3. **Type consistency.** Do types, method signatures, function names, and property names match across all tasks? A function called `save_item()` in Task 3 but `store_item()` in Task 7 is a bug. Check every cross-task reference.

4. **Dependency ordering.** Tasks that depend on earlier tasks must come after them. Check: does any task reference a type, function, or file that isn't created until a later task?

5. **Interface consistency.** Code in later tasks that calls functions defined in earlier tasks must match the exact signature (parameter names, types, return type). Check every call site.

6. **Runnable commands.** Every "Run:" line must be an exact, copy-pasteable command. Every "Expected:" line must describe the exact output or error. No vague expectations like "should work" or "tests pass."

## Response Format

```
### Result: PASS or FAIL

### Issues (if FAIL)
1. [checklist item number]: [specific text that fails] → [what's wrong] → [suggested fix]
2. ...
```
