.claude/agent-memory/ - persistent memory for subagents (shared via git)
========================================================================

Opt-out: delete this folder if no subagent uses `memory: project`.
Claude Code writes here, not you: a subagent with `memory: project` keeps notes
(codepaths, patterns, recurring issues) that survive across conversations.

How it loads
- One folder per subagent:  .claude/agent-memory/<agent-name>/MEMORY.md + topic files
- At launch the subagent gets the first 200 lines / 25KB of its MEMORY.md, plus
  Read/Write/Edit access to its folder. Nothing else here is loaded.
- Requires auto memory on (autoMemoryEnabled / CLAUDE_CODE_DISABLE_AUTO_MEMORY).

Enable it in the agent file, e.g. .claude/agents/test-runner.md:
    ---
    name: test-runner
    description: ...
    memory: project
    ---
    Check your memory for known flaky tests before reporting failures.
    After the run, save new flaky tests and their cause to memory.

Scopes
    project -> .claude/agent-memory/<name>/        committed, shared with the team
    local   -> .claude/agent-memory-local/<name>/  git-ignored (see .gitignore)
    user    -> ~/.claude/agent-memory/<name>/      all your projects

Review memory changes in PRs like code: whatever is committed here, every
teammate's subagent reads.
Docs: https://code.claude.com/docs/en/sub-agents
