# ORC Canary — outside-agent prototype

A small **external** quality probe, not an ORC lane or ORC instruction. No changes to `CLAUDE.md`, `AGENTS.md`, secretary, boss, or other ORC startup files.

## What it does

1. `plan`: Read open GitHub issues in an explicit allowlist using `gh`, ask external `codex exec` for one bounded, real coding task, and save an auditable `runs/<id>/run.json`.
2. `dispatch`: After user review, send a **normal** task to ORC through `courier send secretary`.
3. `assess`: Once ORC returns a PR/commit URL, fetch GitHub's actual changes and have outside `codex exec` produce an independent, evidence-limited review.
4. `install-scheduler.ps1`: Optional Sunday scheduled **plan only**, disabled unless `-Install` is passed. No automatic merge, push, or release.

This is an operational smoke test, **not** a statistically reliable model benchmark. It cannot automatically prove regression from a single run. It does not observe full ORC execution traces or invoke hidden tests. It also does not currently automatically detect task completion; give the resulting PR/commit URL to `assess`.

## Prerequisites (LAB-PC)

- Windows PowerShell 7, Python >= 3.10, GitHub CLI `gh` logged in, external `codex` CLI signed in, `courier` CLI and running dispatcher on the LAB-PC.
- Local access to repositories per `gh` permission. No new Github permissions are needed by this program.
- Put this directory **outside ORC startup material**, e.g. `$DEV\tools\orc-canary`.
- Copy `config.example.json` to `config.json`, check the repository allowlist and target. Use harmless, small projects only. `gh issue list` only covers issues visible to your auth.

## Setup and commands

```powershell
Copy-Item .\config.example.json .\config.json
python .\canary.py plan
# inspect runs/<id>/run.json
python .\canary.py dispatch <id>                 # preview
python .\canary.py dispatch <id> --send          # explicit dispatch
# once ORC creates a PR/commit, independently evaluate its concrete result
python .\canary.py assess <id> --result-url https://github.com/NaNIsaac/hanfix/pull/123

# inspect weekly task; does not change anything
pwsh -File .\install-scheduler.ps1
# register planning-only task, after checking HH:mm and local timezone
pwsh -File .\install-scheduler.ps1 -Install -At 03:00
```

**Important:** Set the allowlist to repos with suitable open issues. If no eligible issues exist the command exits without a task. The external agent's output is schema-validated; only an issue URL already returned by `gh` can be selected. PR/issue text is untrusted, and all subprocesses run without a shell. No code or files from issues are executed.

## Known limitations / next steps

- `codex exec -` semantics must be checked against the locally installed Codex CLI. This prototype expects the CLI to support a stdin prompt. If not, adjust `external_agent()` only.
- `courier doctor` reports failures unrelated to dispatch; if this makes dispatch too strict, replace with a targeted daemon health check, not a silent fallback to direct `herdr agent prompt`.
- `plan --send` allows unattended task dispatch **if explicitly selected**; do not put it in Task Scheduler until safe behavior and current task ownership are verified.
- Independent review is based on diff and GitHub status information; it does not execute the test suite. For a stronger evaluation use a separate disposable worktree and run tests with an explicit per-repository allowlist.
- External AI selection/review incurs API or subscription usage depending on your CLI account. Keep all work off ORC's prompt context.
- A real regression study needs stable benchmark tasks with repeated controlled runs, not only randomly selected GitHub issues.
