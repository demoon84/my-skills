---
name: planwork
description: "Shape an active coding task through focused user conversation, create a dedicated .workloop planning folder, optionally record a Model Strategy, and hand the task off to workloop when execution intent is clear."
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
   - an optional `Model Strategy` when the user cares about speed, cost, depth, or different task shapes
   - any blockers, approvals, or open questions
3. Ask only substantial questions. If the task is already clear enough, summarize the assumptions and continue without creating unnecessary back-and-forth.
4. Once the task is clear, ensure the `.workloop/` root exists. If it is already present, leave it alone and pass.
5. For a new task, create a fresh timestamped child folder such as `.workloop/work_<timestamp>_<slug>/`.
6. Reuse that exact child folder only after it has been chosen for the current task. Do not create a second child folder for every wakeup.
7. Create or update these planning artifacts inside that folder:
   - `task_plan.md`
   - `findings.md`
   - `progress.md`
8. If the user wants recurring background progress, hand the task off to [$workloop](/Users/demoon/Documents/project/mySkills/skills/workloop/SKILL.md) after the plan is stable.
9. Treat clear momentum language such as `continue`, `go ahead`, `keep going`, `진행`, `계속`, or equivalent follow-up approval as permission to create or update the heartbeat without asking again.
10. If the user only wants planning, review, or a draft plan, stop after the plan files are ready and summarized.

## Planning artifact contract

`planwork` owns the planning structure. `workloop` should consume these files instead of inventing a parallel format.

`task_plan.md` should usually contain:

- `Goal`
- `Scope`
- `Constraints`
- `Model Strategy` when it would help the task
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

## Model Strategy

Use `Model Strategy` only when the user explicitly wants model guidance or when the task clearly benefits from documenting which model best fits which subtask.

Treat it as planning metadata, not runtime automation.

- Good fit: "use a deeper model for architecture work and a faster model for narrow cleanup"
- Not in scope: automatic routing, worker orchestration, retries, fallbacks, or model switching logic

When present, keep the section simple and task-oriented. A compact format like this is usually enough:

```text
## Model Strategy

- Task: architecture-heavy refactor
  preferred_model: gpt-5.3-codex
  fallback_model: gpt-5.3-codex-spark
  why: larger cross-file reasoning and safer patch planning

- Task: narrow cleanup or quick follow-up patch
  preferred_model: gpt-5.3-codex-spark
  fallback_model: gpt-5.3-codex
  why: fast iteration with lower overhead
```

The goal is to capture a recommendation the user and agent can both understand later. It is not a command to spawn agents or route work automatically.

## Conversation rules

- Prefer a short planning dialogue over one giant questionnaire.
- If the user asks to "figure it out with me," reflect back a draft plan before starting automation.
- If the user gives relative language like "this folder" or "that bug," translate it into exact paths or outcomes in the plan.
- When the task has risky ambiguity, get user confirmation before turning the plan into an active loop.
- When the task is straightforward and the user clearly wants momentum, create the plan with minimal friction and move forward.

## Auto hand-off defaults

Default to creating or updating `workloop` once the plan is stable when the user's intent already implies continued execution.

Examples that should count as execution intent:

- `continue`
- `go ahead`
- `keep going`
- `진행`
- `계속`
- a follow-up that clearly approves the next implementation step after planning

Do not stop to ask redundant permission in those cases.

Do not auto-start the heartbeat only when one of these is true:

- the user explicitly asked for planning only
- the user asked for review or a draft without execution
- a blocker, approval, or product decision still makes autonomous execution risky

## Hand-off to workloop

Only start or update `workloop` when the planning artifacts are specific enough that repeated wakeups will not drift.

Before handing off, make sure:

1. `Goal` and `Done When` are explicit.
2. The allowed scope or folder boundary is written down.
3. Verification expectations are named.
4. If `Model Strategy` exists, it is clear that it is advisory planning guidance rather than harness behavior.
5. The next highest-priority step is visible from the plan.

When handing off, point `workloop` at the exact planning files and tell it to keep using them.

If the user's intent already implies "plan it and keep going," create or update the heartbeat as the default hand-off instead of stopping after the summary.

Example prompt shape:

```text
Use [$workloop](/Users/demoon/Documents/project/mySkills/skills/workloop/SKILL.md) to create a 1-minute same-thread coding heartbeat for this task. Re-read .workloop/work_<timestamp>_<slug>/task_plan.md, .workloop/work_<timestamp>_<slug>/findings.md, and .workloop/work_<timestamp>_<slug>/progress.md on each wakeup. Keep changes limited to <allowed scope>. Advance the next highest-priority step, verify after code changes, update the planning files, and stop only when the Done When criteria are satisfied or a real blocker requires user input.
```

If the user explicitly asked for planning only, do not create the heartbeat automatically.

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

Use `Model Strategy` only when it adds signal:

```text
## Model Strategy
- Task: repo-wide design or refactor
  preferred_model: gpt-5.3-codex
  why: deeper reasoning across multiple files

- Task: small targeted cleanup
  preferred_model: gpt-5.3-codex-spark
  why: faster narrow iteration
```

## Guardrails

- Do not skip the conversation step just because `workloop` exists.
- Do not create a heartbeat that still depends on missing product decisions.
- Do not leave planning files at repo root when a task-specific `.workloop` folder will isolate them cleanly.
- Do not let `workloop` become the owner of planning semantics; `planwork` defines the plan, `workloop` executes against it.
- Do not let `Model Strategy` turn `planwork` into a harness. Recommendations are fine; automatic routing is not part of this skill.
- Do not force the user to ask for `workloop` twice when execution intent is already obvious from the conversation.
