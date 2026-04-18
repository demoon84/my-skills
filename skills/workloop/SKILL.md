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

## When shaping the prompt

- Describe only the recurring task. Do not put schedule details in the prompt.
- Reuse existing planning artifacts when they exist, especially `task_plan.md`, `findings.md`, `progress.md`, and a main plan doc under `docs/`.
- State any folder boundary explicitly, for example `Keep changes limited to the admin folder.`
- Tell the automation to take the next highest-priority step, not to re-plan from scratch each run.
- Tell it to verify after code changes, then update planning artifacts, then leave a concise status with blockers.
- Tell it to stay quiet unless something important changed when that matters.

## Prompt recipe

Use this shape and swap in the real scope and file paths:

```text
Continue the <scope> work. Re-read <planning files>. Advance the next highest-priority step. Keep changes limited to <allowed scope>. Verify relevant tests or typecheck when code changes are made. Update the planning files. Leave a concise status update with any blockers.
```

If the work already has a stable plan, name the exact files. Prefer explicit file lists over vague references like `review the docs`.

## Good defaults

If planning files already exist:

```text
Continue the current refactor. Re-read task_plan.md, findings.md, progress.md, and docs/<plan>. Advance the next highest-priority step. Verify relevant tests or typecheck when code changes are made. Update the planning files. Leave a concise status update with any blockers.
```

If the user also gave a folder boundary:

```text
Continue the current refactor. Re-read task_plan.md, findings.md, progress.md, and docs/<plan>. Keep changes limited to the admin folder. Advance the next highest-priority step. Verify relevant tests or typecheck when code changes are made. Update the planning files. Leave a concise status update with any blockers.
```

If planning files do not exist yet:

```text
Continue the current coding task. Inspect the latest repo state, take the next highest-priority step, verify after code changes, and leave a concise status update with any blockers.
```

## Lifecycle rules

1. Create a new heartbeat when the user wants recurring background progress.
2. Update the existing heartbeat when the task scope, allowed folder, or plan files change.
3. Pause it only when the user wants a temporary stop.
4. Delete it when the main goal is done, stale, or replaced.
5. Avoid duplicate heartbeats for the same task.

## Guardrails

- Prefer stable prompts that survive many wakeups.
- Do not tell the automation to rewrite unrelated files or roam the repo without bounds.
- Do not embed exact timestamps or schedule text inside the automation prompt.
- Do not create a separate cron automation when the user wants sub-hour cadence in the same thread.
- If the work depends on planning artifacts, make re-reading them part of the prompt instead of assuming memory.

## Example requests

- `Use $workloop to set up a 1-minute loop that keeps pushing this refactor forward.`
- `Use $workloop to make the current admin-only migration continue every minute in this thread.`
- `Use $workloop to create a heartbeat that re-reads task_plan.md, findings.md, and progress.md, then keeps working.`
- `Use $workloop to update the current heartbeat so it only works inside admin/src.`
- `Use $workloop to stop the current 1-minute coding loop.`
