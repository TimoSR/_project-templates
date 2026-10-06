.claude/output-styles/ - team-shared output styles
==================================================

Opt-out: delete this folder if the project doesn't use it.
An output style changes Claude's tone, length, format or role for every response
in a session. Most styles are personal (~/.claude/output-styles/); put one here
only when the whole team shares it, e.g. a review mode.

How it loads
- Every *.md file here is a style. This README is .txt so it doesn't become one.
- Name = file name, or `name:` in frontmatter.
- Select with /output-style <name>, /config, or "outputStyle": "<name>" in settings.
- Read at startup: restart Claude Code after creating or editing a style.

Example: .claude/output-styles/reviewer.md
    ---
    name: Reviewer
    description: Findings first, ranked by severity, no praise
    keep-coding-instructions: true
    ---
    Answer as a code reviewer. List findings as `file:line - problem - fix`,
    most severe first. Skip anything that doesn't affect correctness.

Frontmatter: name, description, keep-coding-instructions (default false = Claude
drops its built-in coding instructions; set true when Claude still writes code).

Not the right tool for:
- project facts and conventions -> CLAUDE.md
- a task-specific procedure    -> skill
- must happen every time       -> hook in settings.json
Docs: https://code.claude.com/docs/en/output-styles
