.claude/workflows/ - saved dynamic workflows
============================================

Opt-out: delete this folder if the project doesn't use it.
A workflow is a JavaScript script that runs many subagents (audits, migrations,
cross-checked research). The script holds the loop and the intermediate results,
so the session only gets the final answer.

How it loads
- Every *.js file here runs as /<meta.name>. This README is .txt, so it's ignored.
- You don't usually write these by hand: ask Claude to "use a workflow" for a task,
  then in /workflows select the run and press `s` to save it here.
- A project workflow wins over a personal one (~/.claude/workflows/) with the same name.
- After editing a script: /reload-skills, then run /<name> again.
  Load the /workflow-authoring skill before editing.

Example: .claude/workflows/audit-resolvers.js
    export const meta = {
      name: 'audit-resolvers',
      description: 'Audit every GraphQL resolver for missing authorization',
    }
    const found = await agent('List every resolver file under API/FF-API/FF.Api.', {
      schema: { type: 'object', required: ['files'],
                properties: { files: { type: 'array', items: { type: 'string' } } } },
    })
    const audits = await pipeline(found.files, file =>
      agent(`Audit ${file} for missing [Authorize] checks.`, { label: file }))
    return audits.filter(Boolean)

Rules
- `export const meta` first, plain literals only (name, description, optional phases).
- No import(), no Date.now()/Math.random(): pass changing values in through `args`.
- Cost: every agent() is a subagent. Try a small slice first.
Docs: https://code.claude.com/docs/en/workflows
