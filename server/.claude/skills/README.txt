.claude/skills/ - on-demand knowledge and workflows
===================================================

Opt-out: delete a skill folder the project doesn't need.
A skill is knowledge or a procedure Claude loads only when the task needs it.
Its description sits in context every session; the body loads on use.

How it loads
- One folder per skill:  .claude/skills/<name>/SKILL.md  -> /<name>
- Claude invokes it on its own when the `description` matches the task, or you
  type /<name>. Files at this top level (like this README) are ignored.
- Other files in the folder load only when SKILL.md links them, so link every
  one directly from SKILL.md (one level deep):
      <name>/
      |-- SKILL.md        entry point, under 500 lines
      |-- reference.md    detail, read on demand (or references/*.md)
      |-- examples.md
      `-- scripts/        code Claude runs instead of reading
- A skill beats a .claude/commands/ file with the same name.
- After /compact, invoked skills come back truncated to their first 5,000
  tokens: put the most important rules at the top.

Example: .claude/skills/hubspot-sync/SKILL.md
    ---
    name: hubspot-sync
    description: Adds or changes a HubSpot CRM field mapping using the
      HubSpotDataMappers<T> pattern. Use when the user mentions HubSpot, deal or
      contact sync, or a CRM field. Not for other integrations (system-integration).
    ---
    # HubSpot sync
    1. Add the mapping in the mapper's constructor ...
    Details: [reference.md](reference.md)

Frontmatter: description (what + when + when not; max 1,536 chars with
when_to_use), name, disable-model-invocation (only /name triggers it),
user-invocable, allowed-tools, paths, context: fork, model, effort.
Before writing or changing a skill, load the `building-skills` skill;
check with: python .claude/skills/building-skills/scripts/validate_skill.py <folder>
Docs: https://code.claude.com/docs/en/skills
