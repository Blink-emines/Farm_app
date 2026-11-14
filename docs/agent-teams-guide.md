# Agent Teams: Master Reference Guide

Source: <https://code.claude.com/docs/en/agent-teams>, read on 2026-11-14 with
Claude Code 2.1.325. Agent teams are **experimental**: recheck the source page
when something here does not match what you see.

Sections 1 to 12 restate the official page. Section 13 is our own plan for the
Farm App and is not from the official page.

---

## 1. What an agent team is

A team is several Claude Code sessions working together:

- One session is the **team lead**. It is the session you are typing in. It
  creates the teammates, hands out work and combines the results.
- The others are **teammates**. Each is a full, separate Claude session with its
  own memory (context window).
- Teammates can **message each other directly**, and you can message any of them.
- They share a **task list**.

Everyday picture: subagents are couriers you send out who come back with a
parcel. A team is a group of colleagues in one room with a shared whiteboard,
who can talk to each other without going through you.

### Teams compared with subagents

| | Subagents | Agent teams |
|---|---|---|
| Context | Own context window; results return to the caller | Own context window; fully independent |
| Communication | Return a result to the caller (named subagents can also message each other) | Teammates message each other directly |
| Coordination | Main agent manages all work | Self-coordination through messages, plus a shared task list |
| Best for | Focused tasks where only the result matters | Complex work requiring discussion and collaboration |
| Token cost | Lower: results summarised back to main context | Higher: each teammate is a separate Claude instance |

Rule of thumb from the docs: use subagents for quick, focused workers that
report back. Use a team when teammates need to share findings, challenge each
other, and coordinate on their own.

## 2. When to use a team, and when not to

Good fits:

- **Research and review**: several angles investigated at once, then compared.
- **New modules or features**: each teammate owns a separate piece.
- **Debugging with competing hypotheses**: each teammate tests a different theory.
- **Cross-layer work**: frontend, backend and tests, each owned by one teammate.

Poor fits (use one session or subagents instead):

- Sequential tasks, where step 2 needs step 1 finished.
- Several agents editing the same files.
- Work with many dependencies between the pieces.

Teams add coordination overhead and use significantly more tokens.

## 3. Turning it on and off

In a settings file (ours is `.claude/settings.local.json`) or as a shell variable:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

- Set it to `"0"` to turn teams off. No new session is needed: the value is
  re-read each time an agent is spawned.
- **Side effect:** while teams are on, any subagent that Claude launches *with a
  name* starts as a teammate, without asking for confirmation. So a team can form
  even when you did not ask for one. If that is unwanted, turn the setting off.
- Teammates can only be spawned in an **interactive** session. With the `-p`
  flag or the Agent SDK, a named agent runs as an ordinary subagent.
- Settings precedence: project, local and `--settings` values apply after user
  settings, so a `1` in our local file wins over a `0` in `~/.claude/settings.json`.

## 4. Starting a team

There is no command. Describe the task and the teammates in plain language:

```text
I'm designing a CLI tool that helps developers track TODO comments across
their codebase. Spawn three teammates to explore this from different angles:
one on UX, one on technical architecture, one playing devil's advocate.
```

Claude may use plain subagents instead. They appear in the same panel, so the
panel alone does not prove a team formed. If that happens, ask again and
explicitly request an agent team.

### The agent panel

It sits below the prompt input in the lead's terminal.

- Idle rows hide 30 seconds after every agent is idle, and come back on the
  teammate's next turn. A hidden teammate is still running and reachable.
- With more than three idle teammates, the extra rows collapse into one row such
  as `2 idle agents`. Select it and press Enter to expand.

### Keyboard shortcuts

| Key | What it does |
|---|---|
| Up / Down | Select a teammate in the panel |
| Enter | Open the selected teammate's transcript and message it |
| Escape | Clear the selection; while viewing a transcript, interrupt that teammate's turn |
| `x` | Stop the selected teammate |
| `Ctrl+T` | Show or hide the task list |
| `Shift+Tab` | Cycle a teammate's permission mode (while viewing it) |

## 5. Display modes

| Mode | What you see | Needs |
|---|---|---|
| **In-process** (default) | All teammates inside the main terminal, reached through the agent panel | Nothing |
| **Split panes** | Each teammate in its own pane | tmux or iTerm2 |

To use split panes, set `teammateMode` in `~/.claude/settings.json`:

```json
{
  "teammateMode": "auto"
}
```

| Value | Behaviour |
|---|---|
| `"auto"` | Split panes inside tmux or iTerm2, in-process elsewhere |
| `"tmux"` | Panes open in a separate tmux session; copy the command from the `View teammates` line to watch them in a second terminal |
| `"iterm2"` | Uses iTerm2's own panes; needs the `it2` CLI and the Python API enabled |

For one session only: `claude --teammate-mode auto` (experimental flag, not shown
in `claude --help`). The docs note tmux works best on macOS.

## 6. Controlling the team

You talk to the lead in plain language; it handles the coordination.

### Number of teammates and their models

```text
Spawn 4 teammates to refactor these modules in parallel. Use Sonnet for
each teammate.
```

A teammate's model is chosen in this order (first that applies wins):

1. The model named in the spawn prompt for that teammate.
2. The `model` in its subagent definition (`inherit` means the lead's model).
3. `CLAUDE_CODE_SUBAGENT_MODEL`, if set to something other than `inherit`.
4. The lead's current model.

A teammate's model is fixed once it is spawned. A teammate on the lead's model
also inherits the lead's effort level.

### Plan before building

Put the lead in plan mode first, then spawn the teammate. It works in plan mode
until its plan is ready:

```text
Spawn an architect teammate to refactor the authentication module.
```

The plan is then approved automatically, without the lead reviewing it, unless
you pressed `Shift+Tab` on that running teammate to put it in plan mode yourself;
in that case the lead reviews the plan. You are never asked to approve a
teammate's plan.

### Talking to a teammate directly

- In-process: select it with the arrows, press Enter, type.
- Split panes: click into its pane.
- While viewing a teammate, plain text and skills go to it. Built-in commands
  still act on the lead: `/compact`, `/clear` and `/rewind` ask for confirmation
  first, and `/model` and `/fast` do not run from this view.

### Tasks

- Three states: pending, in progress, completed.
- A task can depend on others and shows as blocked until they are complete.
  Dependent tasks unblock automatically.
- **Lead assigns**: tell the lead which task goes to which teammate.
- **Self-claim**: a teammate that finishes picks the next unassigned, unblocked
  task. File locking prevents two teammates claiming the same one.

### Shutting down

```text
Ask the researcher teammate to shut down
```

The teammate can accept and exit, or refuse with an explanation. There is no
cleanup step: the team's shared folders are removed when the session ends.

## 7. Using our subagent definitions as teammates

Files in `.claude/agents/` can be used as teammate types:

```text
Spawn a teammate using the security-reviewer agent type to audit the auth module.
```

How each part of the definition is applied:

| Part | In-process teammate | Split-pane teammate |
|---|---|---|
| `tools` | Limited to this list, plus `SendMessage` and the Task tools | Limited to this list |
| `model` | Used when the spawn prompt names no model | Same |
| `disallowedTools` | Removed (except `SendMessage` and Task tools) | Not stated |
| `effort` | Applied | Not stated |
| Body (the instructions) | **Added to** the default system prompt | **Replaces** the default system prompt |
| `skills` | Not applied; skills load from project and user settings | Same |
| `mcpServers` | Ignored; MCP servers load from project and user settings | Applied |

Team membership itself cannot be pre-written in the project. A file such as
`.claude/teams/teams.json` is not recognised. Reusable roles belong in subagent
definitions.

## 8. Quality gates with hooks

| Hook | Runs when | Exit code 2 |
|---|---|---|
| `TeammateIdle` | A teammate is about to go idle | Sends feedback and keeps it working |
| `TaskCreated` | A task is being created | Blocks creation and sends feedback |
| `TaskCompleted` | A task is being marked complete | Blocks completion and sends feedback |

Example use: a `TaskCompleted` hook that runs the tests and refuses "done" when
they fail.

## 9. How it works inside

| Component | Role |
|---|---|
| Team lead | The main session; spawns teammates and coordinates |
| Teammates | Separate Claude Code instances working on assigned tasks |
| Task list | Shared list of work items that teammates claim and complete |
| Mailbox | Messaging system between agents |

Files (managed by Claude Code; do not edit by hand, changes are overwritten):

| What | Where | After the session |
|---|---|---|
| Team config | `~/.claude/teams/{team-name}/config.json` | Removed |
| Mailboxes | `~/.claude/teams/{team-name}/inboxes/{agent-name}.json` | Removed |
| Task list | `~/.claude/tasks/{team-name}/` | Kept (see `cleanupPeriodDays`) |

The team name is `session-` plus the first eight characters of the session ID.

### What a teammate knows

- It loads the normal project context: `CLAUDE.md`, MCP servers and skills.
- It receives the spawn prompt from the lead.
- It does **not** receive the lead's conversation history.

### How information moves

- Messages are delivered automatically; the lead does not poll.
- When a teammate finishes, it notifies the lead with its final answer (or with
  the error text if it failed).
- Any teammate can message another by name. To reach everyone, one message per
  recipient. Tell the lead what to name each teammate so the names are predictable.

### Permissions

- A new teammate starts with the lead's permission mode. Modes cannot be set per
  teammate at spawn; change one afterwards with `Shift+Tab`.
- An in-process teammate runs in the lead's mode while the lead is in
  `acceptEdits`, `auto` or `bypassPermissions`, even if its own bar says Manual.
- Teammate permission prompts appear in the lead session, where you approve them.
- A message from another agent is never treated as your approval. A teammate
  cannot approve a permission prompt for you, and a denied action cannot be
  passed to another teammate to get around the check.

### Cost

Each teammate has its own context window, so token use grows with the number of
active teammates. Worth it for research, review and new features; not for
routine tasks.

## 10. Best practices

1. **Give enough context in the spawn prompt.** Teammates do not see the
   conversation. Example:

   ```text
   Spawn a security reviewer teammate with the prompt: "Review the authentication module
   at src/auth/ for security vulnerabilities. Focus on token handling, session
   management, and input validation. The app uses JWT tokens stored in
   httpOnly cookies. Report any issues with severity ratings."
   ```

2. **Keep the team small.** Start with 3 to 5 teammates. Three focused teammates
   often beat five scattered ones.
3. **Size tasks well.** Each task is a self-contained unit with a clear
   deliverable (a function, a test file, a review). About 5 to 6 tasks per
   teammate keeps everyone busy. If the lead makes too few, ask it to split the work.
4. **Make the lead wait** if it starts doing the work itself:

   ```text
   Wait for your teammates to complete their tasks before proceeding
   ```

5. **Start with research and review.** They need no code writing, so they avoid
   the hard part of parallel work.
6. **Avoid file conflicts.** Two teammates editing one file overwrite each other.
   Give each teammate its own set of files.
7. **Monitor and steer.** Check progress and redirect early; a team left alone
   too long wastes effort.

## 11. Two patterns from the docs

**Parallel review**: each reviewer applies a different filter to the same change.

```text
Spawn three teammates to review PR #142:
- One focused on security implications
- One checking performance impact
- One validating test coverage
Have them each review and report findings.
```

**Competing hypotheses**: teammates try to disprove each other, which avoids
settling on the first plausible explanation.

```text
Users report the app exits after one message instead of staying connected.
Spawn 5 agent teammates to investigate different hypotheses. Have them talk to
each other to try to disprove each other's theories, like a scientific
debate. Update the findings doc with whatever consensus emerges.
```

## 12. Troubleshooting and limits

| Problem | What to do |
|---|---|
| Teammates not appearing | Look in the agent panel; a hidden idle row is not a stopped teammate. Message it by name to bring the row back. The task may also have been too simple for Claude to spawn a team. |
| Split panes not opening | Run `which tmux`; for iTerm2 check the `it2` CLI and the Python API |
| Teammates spawned when you wanted subagents | Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` to `"0"` |
| Too many permission prompts | Pre-approve common commands in permission settings before spawning |
| A teammate stopped early | Open it, read the error, then give instructions or spawn a replacement |
| Lead stopped early | Tell it to keep going |
| tmux session left behind | `tmux ls`, then `tmux kill-session -t <session-name>` |

Known limitations:

- **No resume for in-process teammates.** `/resume` and `/rewind` do not restore
  them; ask the lead to spawn new ones.
- **Task status can lag.** A teammate may forget to mark a task complete and
  block others. Check the work, then update it or have the lead nudge.
- **Shutdown can be slow.** A teammate finishes its current request first.
- **One team per session**, and no sharing a team between sessions.
- **No nested teams.** Only the lead spawns teammates.
- **No background subagents from in-process teammates.**
- **The lead is fixed** for the life of the session.
- **No per-teammate permission mode at spawn.**
- **Split panes need tmux or iTerm2.**

---

## 13. Applying this to the Farm App (our plan, not from the docs)

### Our teammate types

Already defined in `.claude/agents/`:

| Type | Owns | Can edit files |
|---|---|---|
| `data-engineer` | NASA fetch, cleaning, pandas analysis | Yes |
| `backend-developer` | Django models, API, auth | Yes |
| `frontend-developer` | `web/`, later `mobile/` | Yes |
| `qa-security` | Reviews everything | No (read and run only) |

Each already owns different files, which is the main condition for a team to
work without conflicts.

### Where a team helps in our build order

| Layer | Team or not | Why |
|---|---|---|
| 4. NASA fetch | One agent, then `qa-security` | One piece of work in one area |
| 5. Analysis + `/api/results/` | Small team: `data-engineer` + `backend-developer` + `qa-security` | Two owners must agree on the shape of a Result; QA can challenge both |
| 6. React web | `frontend-developer` + `qa-security`; add `backend-developer` if endpoints need changes | Frontend and backend can settle API questions directly |
| 7. Expo mobile | Same as layer 6 | Same reason |
| Any layer | Review team | Parallel review is the safest way to start with teams |

Our layers depend on each other, so a team works **inside one layer**, never
across several layers at once. That keeps the "one layer at a time" rule.

### Spawn prompt template

```text
Create an agent team for layer <N>: <goal in one sentence>.
Spawn these teammates:
- "data" using the data-engineer agent type: <its task and its files>
- "backend" using the backend-developer agent type: <its task and its files>
- "qa" using the qa-security agent type: review each piece when it is done.
Each teammate edits only its own files. "data" and "backend" must agree on
<the shared contract> by message before writing code.
Wait for your teammates to complete their tasks before proceeding.
Done means: <tests pass, qa reports PASS>.
```

### Checklist before spawning

- [ ] Is the work really parallel? If it is one step after another, use one agent.
- [ ] Does each teammate have its own files?
- [ ] Does each spawn prompt carry the context the teammate needs?
- [ ] Is "done" stated in a way that can be checked?
- [ ] Three teammates or fewer to begin with?
