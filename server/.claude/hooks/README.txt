.claude/hooks/ - scripts run by hooks
=====================================

Opt-out: delete a script AND its entry in ../settings.json.
Hooks are commands Claude Code runs at lifecycle events (before a tool call,
after an edit, at stop). Unlike CLAUDE.md, which Claude may ignore, a hook
always runs: use one for anything that must happen every time.

How it loads
- Claude Code never scans this folder. A script runs only because a hook in
  settings.json names it. A script nothing names is dead code.
- Reference scripts from the project root, quoted:
      "command": "node \"$CLAUDE_PROJECT_DIR/.claude/hooks/<script>.mjs\""
- Input: JSON on stdin (tool_name, tool_input, transcript_path, cwd, ...).
- To block a PreToolUse call, exit 0 and print:
      {"hookSpecificOutput":{"hookEventName":"PreToolUse",
        "permissionDecision":"deny","permissionDecisionReason":"<why>"}}
  (or exit 2 with the reason on stderr). Any other exit code = non-blocking error.
- If the script can't decide (bad input), fail open but say so with
  {"systemMessage": "..."}, so broken enforcement doesn't go unnoticed.

Here now
    require-claude-skills.mjs   PreToolUse on Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell.
                                Denies writes to .claude/, CLAUDE.md, AGENTS.md until the
                                session has invoked the skills in rules/claude-config.md.

Example settings.json entry: run a lint script after every edit
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{ "type": "command", "timeout": 60,
                  "command": "node \"$CLAUDE_PROJECT_DIR/.claude/hooks/lint-changed.mjs\"" }]
    }]

Test a script by piping sample input (any readable file with no skill calls
stands in for the transcript, so this prints the deny JSON):
    echo '{"tool_name":"Write","tool_input":{"file_path":"CLAUDE.md"},"transcript_path":".claude/hooks/README.txt"}' | node .claude/hooks/require-claude-skills.mjs
An unreadable transcript_path prints the fail-open systemMessage instead.
Before changing hooks, load the `update-config` skill. Browse active hooks with /hooks.
Docs: https://code.claude.com/docs/en/hooks
