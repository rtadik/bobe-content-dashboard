---
name: plan-and-implement
description: |
  Two-phase workflow for non-trivial codebase changes: (1) /create-plan generates a
  structured implementation plan as a dated markdown file, (2) /implement executes it
  step-by-step with validation. Use when the user says "plan", "create a plan",
  "let's plan this out", "implement the plan", or references a plan file. Also use
  when a task is complex enough to benefit from upfront design before coding.
  Works in any codebase with a plans/ directory.
---

# Plan and Implement

A disciplined "think before you build" workflow. Plans capture the full context, rationale, and step-by-step tasks needed to execute a change. Implementation follows the plan precisely with validation.

## Setup

Create a `plans/` directory in your project root (and optionally `plans/implemented/` for archiving completed plans).

## Two Modes

### Mode 1: Create Plan

**Trigger:** User says "plan", "create a plan for...", or `/create-plan [request]`

1. **Research the codebase** before writing anything:
   - Read project config (CLAUDE.md, README, etc.)
   - Explore areas relevant to the change
   - Understand existing patterns, naming conventions, dependencies

2. **Write the plan** using the template in `references/plan-template.md`
   - Save to `plans/YYYY-MM-DD-{descriptive-name}.md`
   - Use today's date, kebab-case name
   - Fill every section with specific, actionable content
   - No placeholders, no stubs

3. **Report:** Summarize what the plan covers, list open questions, provide the file path, and remind the user to run `/implement` when ready.

### Mode 2: Implement Plan

**Trigger:** User says "implement", "execute the plan", or `/implement [plan-path]`

Follow the protocol in `references/implement-protocol.md`:

1. **Read the plan completely** (not skim)
2. **Check for blockers** (open questions, missing prerequisites)
3. **Execute each step in order**, reading files before modifying
4. **Validate** against the plan's checklist
5. **Update plan status** to Implemented and add implementation notes
6. **Archive** by moving to `plans/implemented/` (if the directory exists)

## Key Principles

- Plans are thorough enough that someone unfamiliar with the project could execute them
- Implementation follows the plan precisely; deviations are documented
- Each plan has a validation checklist and success criteria
- Plans are living documents: status field tracks Draft → Implemented
- Completed plans are archived, not deleted (they serve as project history)

## References

- **`references/plan-template.md`** - Full plan markdown template (read when creating a plan)
- **`references/implement-protocol.md`** - Step-by-step execution protocol (read when implementing)
