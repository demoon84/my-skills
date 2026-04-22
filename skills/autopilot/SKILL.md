---
name: autopilot
description: "Plan a task through conversation into `.autopilot/<slug>_<timestamp>/plan.md`, then keep the agent moving with a Stop hook backed by one Codex thread heartbeat automation until every Done When criterion and every todo is checked."
targets: [codex]
hooks:
  stop: scripts/check-completion.sh
---

# autopilot

A single skill with two modes. Its core purpose is to **keep the agent moving toward the Goal until every `Done When` criterion is satisfied**: whenever the agent tries to finish a turn, a `Stop` hook checks the active run's `plan.md` and, if any `Done When` criterion or todo is still unchecked, tells the agent to keep working. A Codex thread heartbeat automation acts as a backup wake-up path when the hook does not fire, the desktop session loses momentum, or Windows-native hook behavior lags behind macOS/Linux.

The desktop UX constraint matters too: when the agent presents a plan, review, or choice block, that content must remain readable on screen. Do not auto-transition from "showing the user something to read" into "doing more hidden work" in the same turn.

- **Plan mode**: conversation → `.autopilot/<slug>_<timestamp>/plan.md` (goal + scope + done-when + detailed todos)
- **Autopilot mode**: Stop hook guard + one Codex thread heartbeat backup → whenever the agent would stop, re-engage it until every checkbox in `## Done When` and `## Todos` is `[x]`

Each run's `plan.md` is the single source of truth. Do not fragment it into `task_plan.md` / `findings.md` / `progress.md`.

### Workspace model

Every fresh run lives in its own folder under `./.autopilot/`.

- Root folder: `./.autopilot/`
- Thread-scoped pointer: `./.autopilot/threads/<thread-key>.current`
- Global fallback pointer: `./.autopilot/current`
- Run plan file: `./.autopilot/<slug>_<timestamp>/plan.md`

The slug should be short and task-readable, for example `login-copy-update_20260422_101530`.

At the start of a fresh run, bootstrap the workspace with:

- macOS / Linux / WSL: `skills/autopilot/scripts/init-run.sh <slug>`
- Windows: `powershell -File skills/autopilot/scripts/init-run.ps1 <slug>`

When Codex exposes `CODEX_THREAD_ID`, the helper writes the active plan path to `./.autopilot/threads/<thread-key>.current`. It also refreshes `./.autopilot/current` as a compatibility fallback for threadless contexts. The Stop hook trusts the thread-scoped pointer first, then the global fallback.

### Platform behavior

- On macOS / Linux, the installer registers `scripts/check-completion.sh`.
- On Windows, the installer registers `scripts/check-completion.ps1`.
- Inside WSL2, treat the environment as Linux and install the skill from within the distro so Codex registers `scripts/check-completion.sh` in the WSL home.
- The planning contract and `plan.md` behavior stay the same across platforms; only the hook runner changes.

### Automation backup model

- The **Stop hook is primary**. It is the immediate same-turn continuation path.
- The **Codex app heartbeat automation is secondary**. It exists only to re-open this same thread later if the hook path stalls.
- Use **one ACTIVE thread heartbeat** per active run in the current conversation. Reuse/update it; never stack duplicates.
- Use `automation_update` with `kind="heartbeat"` and `destination="thread"`. Prefer a short interval such as every 10 minutes.
- Do **not** use cron automations for `autopilot`. This backup should stay in the same thread so it can resume the thread-scoped active run.
- The heartbeat prompt should tell the future wake-up to resolve `AUTOPILOT_PLAN_PATH` first when explicitly set, otherwise `./.autopilot/threads/<thread-key>.current`, then `./.autopilot/current`; continue only if unchecked items remain and `BLOCKER: true` is absent, and delete or pause itself when the run is complete, paused, or blocked.

### Reward model: Goal over Plan

The reward signal is **Goal completion**, not strict adherence to the original todo list. `plan.md` is split into a locked **Contract** (Goal / Done When / Scope / Verification — the user's agreement) and an adaptive **Execution layer** (Todos / Next Action / Progress Log / Open Decisions — the agent's workspace). The agent may revise Todos mid-flight when reality requires it, as long as the Contract holds and every change is logged. See "plan.md specification" below for the exact rules.

## Mode selection

At the start of each invocation, pick one mode:

| State | User signal | Mode |
|---|---|---|
| No active run pointer and no explicit plan path | any task request | **Plan** |
| Active run exists, unchecked items remain | `진행` / `계속` / `continue` / `go ahead` / `autopilot` | **Autopilot** |
| Active run exists, unchecked items remain | new task description | Ask once using the choice prompt format: `1. 기존 run 이어가기 2. 새 run 만들기 3. 상태 보기 4. 기타` |
| Active run exists, all checked | any task request | Ask once using the choice prompt format: `1. 새 run 만들기 2. 완료된 run 보기 3. 그대로 두기 4. 기타` |
| User explicitly says `계획만` / `plan only` | — | **Plan**, keep the hook disarmed by skipping the transition |
| User says `stop` / `멈춰` / `pause` | — | Disable the hook (temporarily), delete or pause the backup heartbeat automation, and leave the active run untouched |
| User says `status` / `상태` | — | Report progress from the active run `plan.md` (no edits, no hook action) |

Explicit user signals win over implicit state.

## Plan mode

### Clarification protocol

Aim for **2-5 substantive exchanges**. Hard cap: 6.

1. **First turn** — acknowledge the request + ask ONE question about the most uncertain axis (usually Goal).
   Before that first question on a fresh run, bootstrap `.autopilot/<slug>_<timestamp>/plan.md` with the platform-appropriate `init-run` helper and make it the active pointer.
2. **Middle turns** — probe one fact at a time. Never bundle multiple questions.
3. **Reflect-and-confirm** — after every meaningful answer, echo one line before moving on.
4. **Todo draft** — once Goal / Scope / Done When are captured, propose a todo draft for the current run's `plan.md`.
5. **Plan review** — present the full run `plan.md` inline and ask for approval.
6. **Transition** — on approval, save the file and stop so the saved plan stays visible. Start Autopilot execution only on a later explicit momentum phrase (`진행`, `계속`, `continue`, `go ahead`).

Never skip to the draft on the first turn. Always produce at least one reflect-and-confirm exchange.

### Readability guardrail

When the user needs to read or choose:

- Make the approval or choice block the **last visible content** of the turn.
- Do **not** start execution, call extra tools, or emit extra progress chatter after that block unless the user's same message already authorized that exact next step.
- If the plan was just approved and saved, end with a short confirmation such as `저장했습니다. 진행하려면 '진행'이라고 입력해주세요.` and stop there.
- Do not create or update the backup heartbeat on the same turn that only shows the saved plan. Create/update it on the later explicit execution turn.
- Treat this as mandatory for Codex desktop so the reply does not collapse into a compact "worked N seconds" summary before the user has read it.

### Choice prompt format

For every **selection-type question** in `$autopilot`, the agent must present exactly four options:

1. `<recommended / most likely path>`
2. `<second path>`
3. `<third path>`
4. `기타`

Rules:

- Use this format whenever the user is choosing among known paths, approvals, execution modes, or revisions.
- Do **not** use this format for open-ended discovery questions where the user must describe the Goal / Scope / Done When in their own words.
- Put the choice list in the main user-facing reply, not in a progress/update line.
- After a choice list, end the turn immediately unless the user already supplied the choice in the same message.
- When the user picks `4. 기타`, immediately ask for a short free-form reply such as: `원하시는 내용을 짧게 적어주세요.`
- Keep each option label short enough that the user can answer with just `1`, `2`, `3`, or `4`.

### Question bank per planning fact

Pick the one that surfaces the most unknowns. Do not rattle through all of them.

**Goal**
- "끝났을 때 사용자가 볼 수 있는 변화를 한 문장으로?"
- "이 작업이 실패하면 어떤 증상이 남나요?"
- "왜 지금 이걸 해야 하나요?"

**Scope**
- "건드려도 되는 파일/폴더 경계는?"
- "반드시 건드리지 말아야 할 곳은?"
- "기존 API/계약을 깨도 되는지?"

**Done When**
- "어떤 체크리스트가 끝나면 '끝'이라고 말할 수 있나요?"
- "반드시 통과해야 할 검증(테스트/타입체크/빌드) 하나만 꼽으면?"
- "사용자 관점에서 관찰 가능한 변화 2-3개?"

**Verification**
- "변경을 어떤 명령/경로로 확인하나요?"
- "수동 QA가 필요한가요, 자동으로 끝나나요?"

**Constraints / Blockers**
- "시작 전에 필요한 승인·크레덴셜·결정이 있나요?"
- "이번에는 일부러 안 하고 남겨둘 것은?"

### Reflect-and-confirm pattern

After each meaningful answer:

> "확인: <한 줄 요약>."
> "1. 맞아요, 계속"
> "2. 조금 수정"
> "3. 다시 질문"
> "4. 기타"

Skip the echo only when the answer is trivially unambiguous (one-word yes/no, a concrete path).

### Todo quality bar

Every todo in `## Todos` must be:

- **Actionable** — mentions the specific file, function, or command
- **Verifiable** — completion is objectively judgeable
- **Sized to 10-30 minutes** — the agent should be able to finish one todo before it tries to stop again
- **In dependency order** — later todos may assume earlier ones are done

| ❌ Bad | ✅ Good |
|---|---|
| "수정" | "`src/providers/codex.js`의 `createCompletion`이 `sandbox`, `addDir` 파라미터 수용" |
| "검증" | "`npm run check` 실행 및 통과 확인" |
| "깔끔하게 정리" | "`src/lib/skills-install.js` 150자 이상 함수 3개를 분리" |

Phase grouping is **optional**:
- Small task (<10 todos): flat `## Todos` list
- Large task: `### Phase A — <Name>` / `### Phase B — <Name>` blocks with their own todos

### Draft review loop

Before writing the run `plan.md`:

1. Present the **complete** run `plan.md` inline (not just a summary).
2. Ask using the choice prompt format:
   `1. 이대로 저장`
   `2. 저장 후 다음 턴에 진행`
   `3. 한 번 수정`
   `4. 기타`
3. Accept at most **ONE** round of revisions here. Further revisions require re-entering Plan mode.
4. The approval prompt must be the final visible content of the turn. Do not auto-enter execution after showing it.
5. Write the file only after the user chooses `1` or `2`.
6. After saving, end with a short confirmation and stop.
7. Start executing todos only when the user sends a separate momentum message such as `진행` or `continue`. On that first execution turn, create/update the backup thread heartbeat automation, then let the Stop hook take over from there.

### plan.md location

- Default: `./.autopilot/<slug>_<timestamp>/plan.md`.
- The `init-run` helper updates the thread-scoped pointer when `CODEX_THREAD_ID` (or `AUTOPILOT_THREAD_KEY`) is available, and also refreshes `./.autopilot/current` as a fallback.
- Respect an explicit user-provided location if given. When a non-default location is used, set the env var `AUTOPILOT_PLAN_PATH` so the Stop hook can find it.
- Keep compatibility with legacy `./plan.md` or `./.workloop/**/plan.md` only as fallback; new runs should use the `.autopilot/` layout.

## plan.md specification

```markdown
# Plan: <Title>

## Confirmed Decisions
1. ...
2. ...

## Assumed Defaults
- <미지정 항목의 잠정값>

## Goal
<한 문장 + 왜 지금 필요한지>

## Scope
- Allowed: <허용 폴더/파일>
- Out of Scope: <건들지 말 것>

## Done When
- [ ] <사용자 관점 완료 기준 1>
- [ ] <사용자 관점 완료 기준 2>

## Verification
- `<검증 명령 1>`
- `<검증 명령 2>`

## Risks & Mitigations
| Risk | Mitigation |
|---|---|
| ... | ... |

## Todos

### Phase A — <Name>
- [ ] A.1 <구체 작업>
- [ ] A.2 <구체 작업>

### Phase B — <Name>
- [ ] B.1 ...

## Next Action
> <현재 진행할 unchecked todo 1줄>

## Progress Log
(the agent appends lines here)

## Open Decisions
1. <사용자가 결정해야 할 것>

## Model Strategy (optional)
```

Section order is fixed. `plan.md` separates a **Contract** (locked during Autopilot) from an **Execution layer** (adaptive, agent-owned).

### Contract — locked, requires Plan-mode re-entry to change

- `## Goal`
- `## Done When` (text of each criterion; only the `[ ]`/`[x]` state can flip)
- `## Scope` (Allowed / Out of Scope)
- `## Verification` (commands that define "passing")

The agent must NOT edit these during Autopilot. If reality proves a contract item wrong, the agent stops and asks the user to re-enter Plan mode.

### Execution layer — agent may adapt, with an audit trail

- `## Todos` — the agent may:
  - **add** a newly discovered todo (e.g. missing test, pre-req file)
  - **split** a too-large todo into finer ones
  - **refine** a todo's text to be more specific (file path, exact command)
  - **reorder** todos when a dependency is discovered
  - **flip** `[ ]` ↔ `[x]` to mark progress
- `## Next Action` — always points at the current unchecked todo
- `## Progress Log` — append-only
- `## Open Decisions` — append when a blocker surfaces

**Every Todos mutation must be accompanied by a Progress Log line explaining why**, e.g.:

```
2026-04-19 14:22 — A.3 split into A.3a/A.3b: discovered tests were missing
2026-04-19 14:35 — A.5 refined: clarified path to `src/auth/messages.ts`
2026-04-19 15:01 — B.1 added: forgot migration step
```

This keeps the execution layer honest without freezing it.

## Autopilot mode (Stop-hook guard)

Primary execution is not a separate scheduled loop. The agent just **works on the next unchecked todo each turn**, and when it tries to stop the Stop hook checks the active run's `plan.md`. The thread heartbeat automation is only a backup wake-up path when that immediate loop does not keep going.

### Per-turn expectations (the agent's job)

1. Resolve the active run from `AUTOPILOT_PLAN_PATH` when explicitly set, otherwise from `./.autopilot/threads/<thread-key>.current`, then `./.autopilot/current`, then re-read that run's `plan.md` at the start of the turn. Do not rely on memory.
2. Ensure one ACTIVE backup heartbeat automation exists for this thread and active run. Reuse/update the existing heartbeat id when the thread already created one; do not create duplicates.
3. Find the first unchecked todo in `## Todos` (top-down, Phase order).
4. **Sanity-check the todo against reality.** If the todo is underspecified, missing a prerequisite, or reality has shifted, adapt the Execution layer:
   - refine the todo's text to be more specific (exact path/command),
   - split it into smaller todos,
   - insert a missing prerequisite todo before it,
   - reorder when a dependency is discovered.
   
   Any mutation is accompanied by a Progress Log line explaining why (see "Execution layer" above). Never touch the Contract (Goal / Done When / Scope / Verification).
5. Execute the (possibly refined) todo within the declared Scope.
6. If the todo changed code, run the relevant command from `## Verification`.
7. On success, flip `[ ]` → `[x]` in the active run `plan.md`.
8. Update `## Next Action` to the next unchecked todo ("All todos complete" when none remain).
9. Append one line to `## Progress Log`: `YYYY-MM-DD HH:MM — <short summary>`. Skip on no-op turns.

The Goal — not the original todo list — is the reward signal. Todo churn is fine as long as the Contract holds and every change is logged.

### The Stop hook's job

When the agent tries to stop:

- Resolve the active run in this order: `AUTOPILOT_PLAN_PATH` → `./.autopilot/threads/<thread-key>.current` → `./.autopilot/current` → most recent `./.autopilot/*/plan.md` → legacy fallbacks.
- If every `## Done When` entry is `[x]` AND every `## Todos` entry is `[x]` → allow stop. The hook additionally renames that run's `plan.md` → `plan.done.md` and clears both the thread-scoped pointer and `./.autopilot/current` when they still point at the finished run.
- Otherwise → emit `{"hookSpecificOutput": {"hookEventName": "Stop", "decision": "block", "reason": "<n> unchecked items remain. Continue with the next todo."}}` so the agent is forced to continue.

This is implemented in `scripts/check-completion.sh` with a Windows PowerShell counterpart at `scripts/check-completion.ps1`, and auto-registered because this skill declares `hooks.stop` in frontmatter.

### Codex heartbeat backup

When execution starts or resumes:

- Create or update **one** heartbeat automation on the current thread. Suggested name: `autopilot watchdog`.
- Use `kind="heartbeat"`, `destination="thread"`, and `status="ACTIVE"`.
- Prefer a short backup cadence such as every 10 minutes.
- When composing the automation prompt, mention the installed skill as a markdown link with a leading dollar sign, using the platform-local path to `autopilot/SKILL.md`.
- The automation prompt should tell the wake-up run to:
  - use the installed `$autopilot` skill,
  - resolve `AUTOPILOT_PLAN_PATH` first when explicitly set, otherwise the thread-scoped pointer under `.autopilot/threads/`, then `.autopilot/current`,
  - continue only if unchecked `## Done When` or `## Todos` items remain,
  - stop and delete or pause the automation when the run is complete, the user paused it, or `BLOCKER: true` is present.

When the run finishes, pauses, or blocks:

- Delete the backup heartbeat automation.
- If deletion is not possible in that moment, pause it instead.
- Never leave stale active heartbeat automations behind after a finished or paused run.

### Autopilot guardrails

- **Goal is the reward.** Todos are the means. Move toward the Goal; Todos can change, Goal cannot.
- **Contract lock.** Do not change `## Goal`, `## Done When` text, `## Scope`, or `## Verification` during Autopilot. If one of these needs to change, stop and ask the user to re-enter Plan mode.
- **No scope escape.** Do not touch files outside `## Scope > Allowed`.
- **Todos may adapt, but each mutation is logged.** Adding / splitting / refining / reordering a todo is allowed, but the agent MUST append a Progress Log line explaining the change in the same turn. Silent rewrites are forbidden.
- **No todo laundering.** Do not rewrite a failing todo to something trivial just to escape the Stop hook. If a todo fails 3 consecutive turns, record it as a blocker instead (below).
- **No silent verification skip.** If the todo modifies code, the relevant `## Verification` command must run.
- **No infinite grind.** When a todo has failed 3 consecutive turns, append it to `## Open Decisions` with `BLOCKER: true`, and let the agent stop. The user resolves and re-invokes.

### Blocker handling

If the agent cannot proceed (missing credential, ambiguous requirement, failed verification after 3 retries):

1. Append to `## Open Decisions` with a concrete question.
2. Include the line `BLOCKER: true` directly underneath.
3. The Stop hook treats `BLOCKER: true` as "allow stop" — the user must resolve the blocker and re-invoke autopilot.
4. The backup heartbeat automation should delete or pause itself once the blocker is recorded.

### Status reporting

When the user asks `status` / `상태`:
- Resolve the active run first from `AUTOPILOT_PLAN_PATH`, otherwise the thread-scoped pointer under `.autopilot/threads/`, then `.autopilot/current`.
- Count checked vs total todos in `## Done When` and `## Todos`.
- Show the current `## Next Action`.
- Show the last entry in `## Progress Log`.
- Show any `## Open Decisions`.

Read the active run `plan.md` only; do not advance any todo.

## Transition: Plan → Autopilot

After the run `plan.md` is written in Plan mode:

- **Start executing** when the user says `진행` / `계속` / `continue` / `go ahead` / `autopilot`. On that first execution turn, create/update the single backup heartbeat automation for this thread, then process the first unchecked todo; the Stop hook handles immediate continuation after that.
- **Do not execute** when the user says `계획만` / `plan only` / `지금은 멈춰` / explicit `stop`.
- If signal is ambiguous, ask exactly once using the choice prompt format:
  `1. 지금 바로 실행`
  `2. 계획만 저장`
  `3. 상태만 보기`
  `4. 기타`

## Guardrails

- `autopilot` owns the active run `plan.md`. No other tool should mutate it mid-flight.
- Keep each run `plan.md` concise. Move long-form detail into linked docs; todos carry the step-by-step.
- Contract sections (`## Goal`, `## Done When`, `## Scope`, `## Verification`) are locked in Autopilot mode. Changing any of them requires an explicit Plan-mode re-invocation by the user.
- Execution sections (`## Todos`, `## Next Action`, `## Progress Log`, `## Open Decisions`) are agent-owned; every Todos mutation must carry a Progress Log justification in the same turn.
- Preserve `plan.md` section order. Do not rename or drop sections.
- Never delete a run `plan.md` automatically. On completion, the hook renames it to `plan.done.md`.
- Do not create cron automations or external schedulers. `autopilot` may use one thread heartbeat automation as a backup, but the Stop hook remains the primary loop.
- Do not create duplicate active heartbeat automations for the same run/thread. Update the existing one instead.

## Example prompts

- `$autopilot: 로그인 에러 메시지 개선. 계획부터 잡자.` → Plan mode
- `$autopilot: 진행해` → Execute first todo; Stop hook loops until done
- `$autopilot: 계획만` → Plan mode, no execution
- `$autopilot: stop` → disable the hook, keep the active `.autopilot/<slug>_<timestamp>` run
- `$autopilot: status` → print progress from the active run `plan.md`

### Example choice prompts

When continuing vs replacing an existing plan:

1. 기존 plan 이어가기
2. 새로 짜기
3. 상태 보기
4. 기타

If the user replies `4`, follow immediately with:

`원하시는 방향을 짧게 적어주세요.`

When reviewing the final plan draft:

1. 이대로 저장
2. 저장 후 다음 턴에 진행
3. 한 번 수정
4. 기타
