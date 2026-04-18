---
name: workloop
description: Create or update a 1-minute same-thread coding heartbeat that keeps working on an active task in the background. Use when the user wants Codex to continue a refactor, migration, bugfix, or rollout every minute by re-reading planning files, advancing the next highest-priority step, verifying changes, updating progress artifacts, and posting concise status or blockers.
---

# Workloop

Create a thread heartbeat for active coding work that should keep moving without the user manually prompting each step.

## Default configuration

- Prefer a thread heartbeat, not a cron automation.
- Use `kind="heartbeat"` and `destination="thread"`.
- Use `rrule="FREQ=MINUTELY;INTERVAL=1"`.
- Default `status` to `ACTIVE` unless the user asks to start paused.
- If the user does not provide a name, use a short name such as `Refactor Loop` or `Workloop`.

## Planning directory convention

- Do not default to root-level `task_plan.md`, `findings.md`, or `progress.md`.
- Prefer a task-specific folder under `.workloop/`, ideally one prepared by [$planwork](/Users/demoon/Documents/project/mySkills/skills/planwork/SKILL.md).
- If `.workloop/` already exists, leave it in place and do not recreate or reset it.
- If `.workloop/` does not exist yet, create it once and use it as the parent container for future task folders.
- A directory such as `.workloop/work_20260418_154812/` is acceptable, and `.workloop/work_20260418_154812_<slug>/` is even better when the task name should stay visible.
- For a new task or fresh planning session, create a new timestamp-based child folder under `.workloop/` instead of overwriting an older task folder.
- Store planning artifacts in that folder:
  - `.workloop/work_<timestamp>/task_plan.md`
  - `.workloop/work_<timestamp>/findings.md`
  - `.workloop/work_<timestamp>/progress.md`
- Once a child folder has been chosen for the current task, reuse that exact `.workloop/work_*` folder across wakeups instead of creating a new one every run.
- If the user already has another established planning location and explicitly wants to keep it, respect that instead of forcing `.workloop/`.

## Integration with planwork

- If [$planwork](/Users/demoon/Documents/project/mySkills/skills/planwork/SKILL.md) prepared the planning files, treat them as the source of truth for scope, `Done When`, verification, and blockers.
- Re-read the exact `task_plan.md`, `findings.md`, and `progress.md` files on every wakeup instead of reconstructing the plan from memory.
- If the task plan includes a `Model Strategy`, treat it as advisory planning context only.
- Do not silently loosen `Done When` or scope boundaries that came from `planwork`.
- Do not treat `Model Strategy` as permission to auto-route models, spawn workers, or turn the loop into a harness.
- If the planning files still show unresolved questions that require user direction, stop execution and report the blocker instead of drifting into guesses.

## When shaping the prompt

- Describe only the recurring task. Do not put schedule details in the prompt.
- Reuse existing planning artifacts when they exist, especially the files inside the active `.workloop/work_*` folder and any main plan doc under `docs/`.
- If a task was prepared by `planwork`, keep execution aligned with the plan instead of reopening the planning conversation on every wakeup.
- If a plan includes `Model Strategy`, keep it read-only unless the user explicitly asks to revise the plan.
- State any folder boundary explicitly, for example `Keep changes limited to the admin folder.`
- Tell the automation to take the next highest-priority step, not to re-plan from scratch each run.
- Tell the automation to keep working until the goal is actually complete, not merely advanced.
- Tell it to verify after code changes, then update planning artifacts, then leave a concise status with blockers.
- Tell it to stay quiet unless something important changed when that matters.
- Name the exact `.workloop` directory in the prompt so future wakeups keep using the same files.

## Definition of done

Treat the task as complete only when all of the following are true:

1. The requested user-visible outcome is implemented, not just partially advanced.
2. The work stays within the allowed scope or folder boundary.
3. Relevant verification has passed after the latest code changes, such as tests, typecheck, build, or another directly relevant check.
4. No unresolved high-priority blocker remains for that task in the active `.workloop/work_*` folder.
5. The planning artifacts in the active `.workloop/work_*` folder are updated to reflect the final state.

When useful, tell the automation to maintain a `Done When` section near the top of `.workloop/work_<timestamp>/task_plan.md` so completion stays explicit across wakeups.

Example:

```text
Done when:
- The requested feature or fix works end to end
- Relevant tests or checks pass
- No P0 or P1 blockers remain for this task
- .workloop/work_<timestamp>/progress.md reflects the final status
```

## Stop conditions

Tell the automation to stop advancing the task only when one of these is true:

1. All completion criteria are satisfied.
2. A real blocker requires user input, credentials, external approval, or a product decision.
3. Requirements conflict in a way that would make autonomous guessing risky.

When blocked, tell it to avoid drifting into unrelated work. It should record the blocker clearly in the active `.workloop/work_*` folder and leave a concise status update.

## Prompt recipe

Use this shape and swap in the real scope and file paths:

```text
Continue the <scope> work. Re-read <planning files>. Advance the next highest-priority step. Keep changes limited to <allowed scope>. Keep working until the goal is fully complete, not just partially advanced. Verify relevant tests or typecheck when code changes are made. Update the planning files. Leave a concise status update with any blockers.
```

If the work already has a stable plan, name the exact files. Prefer explicit file lists over vague references like `review the docs`.

## Good defaults

If planning files already exist in a `.workloop` folder:

```text
Continue the current refactor. Re-read .workloop/work_<timestamp>/task_plan.md, .workloop/work_<timestamp>/findings.md, .workloop/work_<timestamp>/progress.md, and docs/<plan>. Advance the next highest-priority step. Keep working until the goal is fully complete, not just partially advanced. Verify relevant tests or typecheck when code changes are made. Update the planning files. Treat the task as done only when the requested outcome is implemented, relevant verification passes, no P0 or P1 blockers remain, and the planning files reflect the final state. Leave a concise status update with any blockers.
```

If the user also gave a folder boundary:

```text
Continue the current refactor. Re-read .workloop/work_<timestamp>/task_plan.md, .workloop/work_<timestamp>/findings.md, .workloop/work_<timestamp>/progress.md, and docs/<plan>. Keep changes limited to the admin folder. Advance the next highest-priority step. Keep working until the goal is fully complete, not just partially advanced. Verify relevant tests or typecheck when code changes are made. Update the planning files. Treat the task as done only when the requested outcome is implemented, relevant verification passes, no P0 or P1 blockers remain, and the planning files reflect the final state. Leave a concise status update with any blockers.
```

If planning files do not exist yet, create `.workloop/` only if it is missing, then create a fresh timestamped child folder for this task and use it from then on:

```text
Continue the current coding task. Use .workloop/work_<timestamp>/task_plan.md, .workloop/work_<timestamp>/findings.md, and .workloop/work_<timestamp>/progress.md as the planning files for this task. Add a short Done When section near the top of the task plan. Inspect the latest repo state, take the next highest-priority step, keep working until the goal is fully complete, verify after code changes, update those planning files, and leave a concise status update with any blockers.
```

## Lifecycle rules

1. Create a new heartbeat when the user wants recurring background progress.
2. When creating a new loop for a new task, keep the existing `.workloop/` root if it is already there, then create a fresh timestamped `.workloop/work_*` child folder for that task.
3. Update the existing heartbeat when the task scope, allowed folder, or plan files change.
4. Reuse only the matching `.workloop/work_*` folder for the active task, and do not overwrite planning files from unrelated older task folders.
5. Pause it only when the user wants a temporary stop.
6. Delete it when the main goal is done, stale, or replaced.
7. Avoid duplicate heartbeats for the same task.

## Guardrails

- Prefer stable prompts that survive many wakeups.
- Do not tell the automation to rewrite unrelated files or roam the repo without bounds.
- Do not embed exact timestamps or schedule text inside the automation prompt.
- Do not create a separate cron automation when the user wants sub-hour cadence in the same thread.
- If the work depends on planning artifacts, make re-reading them part of the prompt instead of assuming memory.
- Do not scatter multiple unrelated planning files at repo root when a `.workloop/work_*` folder will keep the task isolated.
- Do not turn an advisory `Model Strategy` section into implicit runtime routing behavior.

## Example requests

- `Use $workloop to set up a 1-minute loop that keeps pushing this refactor forward.`
- `Use $workloop to make the current admin-only migration continue every minute in this thread.`
- `Use $workloop to create a heartbeat that re-reads .workloop/work_20260418_154812/task_plan.md, findings.md, and progress.md, then keeps working.`
- `Use $planwork first to shape the task, then use $workloop to execute the approved plan every minute.`
- `Use $workloop to update the current heartbeat so it only works inside admin/src.`
- `Use $workloop to stop the current 1-minute coding loop.`
