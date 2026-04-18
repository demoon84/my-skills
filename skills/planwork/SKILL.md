---
name: planwork
description: "Shape an active coding task through focused user conversation, create a dedicated .workloop planning folder, and prepare workloop-ready plan files when the goal, scope, and done criteria are clear."
---

# Planwork

Use this skill when the task is still fuzzy enough that Codex should slow down, confirm the right scope with the user, and write a stable plan before background execution begins.

## When to use

- Use when the user wants to talk through a task before implementation starts.
- Use when the user wants a clean `.workloop` planning folder for one task.
- Use when `workloop` would be useful, but only after the task has been clarified enough to execute repeatedly.
- Use when the task needs explicit scope boundaries, verification expectations, or a `Done When` checklist before automation begins.

## Workflow

1. Start with focused clarification, not immediate execution.
2. Confirm the minimum set of planning facts:
   - the goal or user-visible outcome
   - the allowed repo or folder scope
   - key constraints or non-goals
   - how success will be verified
   - what counts as done
   - any blockers, approvals, or open questions
3. Ask only substantial questions. If the task is already clear enough, summarize the assumptions and continue without creating unnecessary back-and-forth.
4. Once the task is clear, create or reuse one task folder under `.workloop/`.
5. Prefer a directory name like `.workloop/work_<timestamp>_<slug>/`. If a stable folder already exists for the same task, reuse it instead of creating a second one.
6. Create or update these planning artifacts inside that folder:
   - `task_plan.md`
   - `findings.md`
   - `progress.md`
7. If the user wants recurring background progress, hand the task off to [$workloop](/Users/demoon/Documents/project/mySkills/skills/workloop/SKILL.md) after the plan is stable.
8. If the user only wants planning, stop after the plan files are ready and summarized.

## Planning artifact contract

`planwork` owns the planning structure. `workloop` should consume these files instead of inventing a parallel format.

`task_plan.md` should usually contain:

- `Goal`
- `Scope`
- `Constraints`
- `Done When`
- `Verification`
- `Open Questions`
- `Next Steps`

`findings.md` should capture:

- confirmed facts from the repo or user conversation
- important risks or assumptions
- blockers or decisions that affect execution

`progress.md` should capture:

- current status such as `planning`, `active`, `blocked`, or `done`
- the latest meaningful update
- the next expected action

Keep these files concise and current. Do not let them become a second long-form spec unless the task truly needs it.

## Conversation rules

- Prefer a short planning dialogue over one giant questionnaire.
- If the user asks to "figure it out with me," reflect back a draft plan before starting automation.
- If the user gives relative language like "this folder" or "that bug," translate it into exact paths or outcomes in the plan.
- When the task has risky ambiguity, get user confirmation before turning the plan into an active loop.
- When the task is straightforward and the user clearly wants momentum, create the plan with minimal friction and move forward.

## Hand-off to workloop

Only start or update `workloop` when the planning artifacts are specific enough that repeated wakeups will not drift.

Before handing off, make sure:

1. `Goal` and `Done When` are explicit.
2. The allowed scope or folder boundary is written down.
3. Verification expectations are named.
4. The next highest-priority step is visible from the plan.

When handing off, point `workloop` at the exact planning files and tell it to keep using them.

Example prompt shape:

```text
Use [$workloop](/Users/demoon/Documents/project/mySkills/skills/workloop/SKILL.md) to create a 1-minute same-thread coding heartbeat for this task. Re-read .workloop/work_<timestamp>_<slug>/task_plan.md, .workloop/work_<timestamp>_<slug>/findings.md, and .workloop/work_<timestamp>_<slug>/progress.md on each wakeup. Keep changes limited to <allowed scope>. Advance the next highest-priority step, verify after code changes, update the planning files, and stop only when the Done When criteria are satisfied or a real blocker requires user input.
```

If the user did not ask for recurring execution, do not create the heartbeat automatically.

## Good defaults

Use a planning folder like:

```text
.workloop/work_20260418_173500_planwork-integration/
```

Use a `Done When` section that stays user-facing and concrete:

```text
Done when:
- The new skill exists and is installed locally
- workloop reuses the planwork planning files
- Relevant metadata is refreshed and validated
```

## Guardrails

- Do not skip the conversation step just because `workloop` exists.
- Do not create a heartbeat that still depends on missing product decisions.
- Do not leave planning files at repo root when a task-specific `.workloop` folder will isolate them cleanly.
- Do not let `workloop` become the owner of planning semantics; `planwork` defines the plan, `workloop` executes against it.
