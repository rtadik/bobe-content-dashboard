# Implement Protocol

Follow these phases in order when executing a plan.

---

## Phase 1: Understand the Plan

1. **Read the plan file completely.** Do not skim.
2. **Verify prerequisites:**
   - Are there open questions that need answers first?
   - Are there dependencies on external resources or user decisions?
   - If blockers exist, stop and ask the user before proceeding.
3. **Confirm readiness:**
   - Status should be "Draft" or "Ready"
   - All sections should be filled out (no placeholder text remaining)

---

## Phase 2: Execute

1. **Follow Step-by-Step Tasks in exact order.**
   - Complete each step fully before moving to the next
   - If creating a file, write the complete file (not a stub)
   - If modifying a file, read it first, then apply changes precisely

2. **For each task:**
   - Read any files that will be affected
   - Make the changes specified
   - Verify the change is correct before proceeding

3. **Handle issues gracefully:**
   - If a step can't be completed as written, adapt if the intent is clear
   - If unsure how to proceed, ask rather than guess
   - Document any deviations from the plan

---

## Phase 3: Validate

1. **Run through the Validation Checklist** from the plan
   - Check off each item
   - Note any that fail

2. **Verify Success Criteria** are met

3. **Check cross-references and consistency:**
   - New files are referenced where they should be
   - Project documentation is updated if structure changed
   - Naming conventions are followed

---

## Phase 4: Update Plan Status

After implementation, update the plan file:

1. Change `**Status:** Draft` to `**Status:** Implemented`
2. Add this section at the end of the plan:

```markdown
---

## Implementation Notes

**Implemented:** <YYYY-MM-DD>

### Summary

<Brief summary of what was done>

### Deviations from Plan

<List any changes made during implementation, or "None">

### Issues Encountered

<Problems hit and how they were resolved, or "None">
```

3. Move the plan to `plans/implemented/` (if the directory exists)

---

## Report Format

After implementation, provide:

```
## Implementation Complete

### Summary
- <What was done>
- <What was done>

### Files Changed
**Created:**
- `path/to/new-file`

**Modified:**
- `path/to/modified-file`

**Deleted:**
- (none)

### Validation
- [x] <Passed check>
- [x] <Passed check>

### Deviations from Plan
<None, or list deviations>

### Plan Status
Updated plan status to "Implemented"
```
