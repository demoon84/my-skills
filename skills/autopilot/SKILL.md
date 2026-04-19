---
name: autopilot
description: "Plan a task through conversation into plan.md, then keep the agent from stopping via a Stop hook until every Done When criterion and every todo is checked."
targets: [claude, codex, gemini]
hooks:
  stop: scripts/check-completion.sh
---

# autopilot

A single skill with two modes. Its core purpose is to **keep the agent moving toward the Goal until every `Done When` criterion is satisfied**: whenever the agent tries to finish a turn, a `Stop` hook checks `plan.md` and, if any `Done When` criterion or todo is still unchecked, tells the agent to keep working.

- **Plan mode**: conversation → `plan.md` (goal + scope + done-when + detailed todos)
- **Autopilot mode**: Stop hook guard → whenever the agent would stop, re-engage it until every checkbox in `## Done When` and `## Todos` is `[x]`

`plan.md` is the single source of truth. Do not fragment it into `task_plan.md` / `findings.md` / `progress.md`.

### Reward model: Goal over Plan

The reward signal is **Goal completion**, not strict adherence to the original todo list. `plan.md` is split into a locked **Contract** (Goal / Done When / Scope / Verification — the user's agreement) and an adaptive **Execution layer** (Todos / Next Action / Progress Log / Open Decisions — the agent's workspace). The agent may revise Todos mid-flight when reality requires it, as long as the Contract holds and every change is logged. See "plan.md specification" below for the exact rules.

## Mode selection

At the start of each invocation, pick one mode:

| State | User signal | Mode |
|---|---|---|
| `plan.md` missing | any task request | **Plan** |
| `plan.md` exists, unchecked items remain | `진행` / `계속` / `continue` / `go ahead` / `autopilot` | **Autopilot** |
| `plan.md` exists, unchecked items remain | new task description | Ask once: "기존 plan 이어갈까요, 새로 짤까요?" |
| `plan.md` exists, all checked | any task request | Ask once: "완료된 plan 있음. 새로 짤까요?" |
| User explicitly says `계획만` / `plan only` | — | **Plan**, keep the hook disarmed by skipping the transition |
| User says `stop` / `멈춰` / `pause` | — | Disable the hook (temporarily) and leave `plan.md` untouched |
| User says `status` / `상태` | — | Report progress from `plan.md` (no edits, no hook action) |

Explicit user signals win over implicit state.

## Plan mode

### Clarification protocol

Aim for **2-5 substantive exchanges**. Hard cap: 6.

1. **First turn** — acknowledge the request + ask ONE question about the most uncertain axis (usually Goal).
2. **Middle turns** — probe one fact at a time. Never bundle multiple questions.
3. **Reflect-and-confirm** — after every meaningful answer, echo one line before moving on.
4. **Todo draft** — once Goal / Scope / Done When are captured, propose a todo draft.
5. **Plan review** — present the full `plan.md` inline and ask for approval.
6. **Transition** — on approval, save the file. On a momentum phrase (`진행`, `계속`, `continue`, `go ahead`), save AND proceed to execute the first unchecked todo immediately.

Never skip to the draft on the first turn. Always produce at least one reflect-and-confirm exchange.

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

> "확인: <한 줄 요약>. 이대로 진행할게요, 수정할 부분 있나요?"

Skip the echo only when the answer is trivially unambiguous (one-word yes/no, a concrete path).

### Todo quality bar

Every todo in `## Todos` must be:

- **Actionable** — mentions the specific file, function, or command
- **Verifiable** — completion is objectively judgeable
- **Sized to 10-30 minutes** — the agent should be able to finish one todo before it tries to stop again
- **In dependency order** — later todos may assume earlier ones are done

| ❌ Bad | ✅ Good |
|---|---|
| "Claude 수정" | "`src/providers/claude.js`의 `createCompletion`이 `permissionMode`, `addDir` 파라미터 수용" |
| "검증" | "`npm run check` 실행 및 통과 확인" |
| "깔끔하게 정리" | "`src/lib/skills-install.js` 150자 이상 함수 3개를 분리" |

Phase grouping is **optional**:
- Small task (<10 todos): flat `## Todos` list
- Large task: `### Phase A — <Name>` / `### Phase B — <Name>` blocks with their own todos

### Draft review loop

Before writing `plan.md`:

1. Present the **complete** `plan.md` inline (not just a summary).
2. Ask: "이대로 `./plan.md`에 저장할게요. 고칠 부분?"
3. Accept at most **ONE** round of revisions here. Further revisions require re-entering Plan mode.
4. Write the file.
5. If the user signals execution intent, proceed to handle the first unchecked todo immediately. The Stop hook takes over from there.

### plan.md location

- Default: `./plan.md` at the repo root.
- Optional isolation: `.workloop/work_<timestamp>_<slug>/plan.md` when the user runs multiple concurrent tasks.
- Respect an explicit user-provided location if given. When a non-default location is used, set the env var `AUTOPILOT_PLAN_PATH` so the Stop hook can find it.

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

Execution is not a separate scheduled loop. The agent just **works on the next unchecked todo each turn**, and when it tries to stop the Stop hook checks `plan.md`.

### Per-turn expectations (the agent's job)

1. Re-read `plan.md` at the start of the turn. Do not rely on memory.
2. Find the first unchecked todo in `## Todos` (top-down, Phase order).
3. **Sanity-check the todo against reality.** If the todo is underspecified, missing a prerequisite, or reality has shifted, adapt the Execution layer:
   - refine the todo's text to be more specific (exact path/command),
   - split it into smaller todos,
   - insert a missing prerequisite todo before it,
   - reorder when a dependency is discovered.
   
   Any mutation is accompanied by a Progress Log line explaining why (see "Execution layer" above). Never touch the Contract (Goal / Done When / Scope / Verification).
4. Execute the (possibly refined) todo within the declared Scope.
5. If the todo changed code, run the relevant command from `## Verification`.
6. On success, flip `[ ]` → `[x]` in `plan.md`.
7. Update `## Next Action` to the next unchecked todo ("All todos complete" when none remain).
8. Append one line to `## Progress Log`: `YYYY-MM-DD HH:MM — <short summary>`. Skip on no-op turns.

The Goal — not the original todo list — is the reward signal. Todo churn is fine as long as the Contract holds and every change is logged.

### The Stop hook's job

When the agent tries to stop:

- If every `## Done When` entry is `[x]` AND every `## Todos` entry is `[x]` → allow stop. The hook additionally renames `plan.md` → `plan.done.md`.
- Otherwise → emit `{"hookSpecificOutput": {"hookEventName": "Stop", "decision": "block", "reason": "<n> unchecked items remain. Continue with the next todo."}}` so the agent is forced to continue.

This is implemented in `scripts/check-completion.sh` and auto-registered because this skill declares `hooks.stop` in frontmatter.

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

### Status reporting

When the user asks `status` / `상태`:
- Count checked vs total todos in `## Done When` and `## Todos`.
- Show the current `## Next Action`.
- Show the last entry in `## Progress Log`.
- Show any `## Open Decisions`.

Read `plan.md` only; do not advance any todo.

## Transition: Plan → Autopilot

After `plan.md` is written in Plan mode:

- **Start executing** when the user says `진행` / `계속` / `continue` / `go ahead` / `autopilot`. The agent processes the first unchecked todo; the Stop hook handles everything after.
- **Do not execute** when the user says `계획만` / `plan only` / `지금은 멈춰` / explicit `stop`.
- If signal is ambiguous, ask exactly once: "지금 바로 실행 시작할까요?"

## Guardrails

- `autopilot` owns `plan.md`. No other tool should mutate it mid-flight.
- Keep `plan.md` concise. Move long-form detail into linked docs; todos carry the step-by-step.
- Contract sections (`## Goal`, `## Done When`, `## Scope`, `## Verification`) are locked in Autopilot mode. Changing any of them requires an explicit Plan-mode re-invocation by the user.
- Execution sections (`## Todos`, `## Next Action`, `## Progress Log`, `## Open Decisions`) are agent-owned; every Todos mutation must carry a Progress Log justification in the same turn.
- Preserve `plan.md` section order. Do not rename or drop sections.
- Never delete `plan.md` automatically. On completion, the hook renames it to `plan.done.md`.
- Do not create cron jobs, Claude Routines, Codex automations, or external schedulers. Autopilot runs via the Stop hook, nothing else.

## Example prompts

- `$autopilot: 로그인 에러 메시지 개선. 계획부터 잡자.` → Plan mode
- `$autopilot: 진행해` → Execute first todo; Stop hook loops until done
- `$autopilot: 계획만` → Plan mode, no execution
- `$autopilot: stop` → disable the hook, keep `plan.md`
- `$autopilot: status` → print progress from `plan.md`
