.claude/agents/ - subagents
===========================

Opt-out: delete an agent file (or the folder) if the project doesn't use it.
A subagent runs a focused task in its own context window and returns only a
summary, so read-heavy or noisy work (test runs, broad searches, reviews)
doesn't fill the main session.

How it loads
- Every *.md file here with `name` + `description` frontmatter is an agent.
  Files without `name` are skipped as docs; this README is .txt anyway.
- Claude delegates on its own when the `description` matches the task
  ("Use PROACTIVELY after ..." encourages it), or when asked: "use test-runner".
- The body after the frontmatter is the agent's system prompt. It gets its own
  copy of CLAUDE.md, but none of the main conversation.
- Same name at several levels: managed > --agents flag > project > user > plugin.

Here now
    test-runner.md   runs FF.Tests, reports pass/fail/skip; read-only (Bash, Read, Grep, Glob)

Example: .claude/agents/migration-reviewer.md
    ---
    name: migration-reviewer
    description: Reviews EF Core migrations under API/FF-API/FF.Core/Migrations for data loss
      and locking. Use PROACTIVELY after `dotnet ef migrations add`.
    tools: Read, Grep, Glob
    model: sonnet
    ---
    Review the newest migration. Report dropped columns, NOT NULL without a default,
    and index builds on large tables, as `file:line - risk - fix`.

Frontmatter: name (no `:`), description (required); optional tools, disallowedTools,
model, permissionMode, maxTurns, skills, mcpServers, hooks, memory (see
../agent-memory/README.txt), effort, isolation: worktree, color.
Docs: https://code.claude.com/docs/en/sub-agents
