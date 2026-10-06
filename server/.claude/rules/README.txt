.claude/rules/ - instructions scoped to files
=============================================

Opt-out: delete a rule that doesn't apply to the project.
A rule is a short CLAUDE.md fragment. With `paths:` it loads only when Claude
Reads, Writes or Edits a matching file; without `paths:` it loads every session.

WARNING: every *.md file here is a rule, including subfolders. A README.md here
would load into every session, which is why this file is .txt.

How it loads
- `paths:` globs are relative to the project root; brace expansion works.
  `paths` is the only frontmatter field read. YAML that doesn't parse makes the
  rule load unconditionally.
- Loaded rules stay in context. After /compact, path rules are dropped until a
  matching file is touched again; rules without `paths:` are re-injected.
- A rule whose globs match no file never loads. Check after moving folders:
      git ls-files "<glob>" | head
- A skill that is a standard (always followed for some files) is imported, not
  copied: the rule keeps the repo-specific lines, then `@../skills/<name>/SKILL.md`.
  The whole skill loads with the rule; the skill stays the one place to edit it.
  The skill remains invocable on its own (/<name>) for its supporting files.

Here now (no `paths:` = always loaded: every session start, re-injected after /compact)
    claude-config.md            .claude/**, CLAUDE.md, AGENTS.md   which skills to load before editing Claude config
    development.md              always                             think first, simplicity, surgical changes
    code-style.md               always                             imports c-like-coding-style
    financial-code.md           always                             imports codemath
    logging.md                  always                             imports logging
    persistence.md              always                             imports database-design
    rest-api.md                 always                             imports api-design
    security.md                 always                             imports security
    tests.md                    *Test(s).*, *.test/spec.*, test_*  imports tests-as-documentation
    solid-principles.md         always                             imports solid-principles
    design-patterns.md          always                             imports design-patterns
    microservices-patterns.md   always                             imports microservices-patterns
    system-integration.md       always                             imports system-integration
    low-level-optimizations.md  always                             imports low-level-optimizations

Example: .claude/rules/migrations.md
    ---
    paths:
      - "API/FF-API/FF.Core/Migrations/**/*.cs"
    ---
    # Migrations
    - Never edit an applied migration; add a new one.
    - Review the generated SQL with `dotnet ef migrations script` before committing.

Verify a new rule: fresh session, Read a matching file, then /context shows it
under Memory files.
Docs: https://code.claude.com/docs/en/memory
