# Claude Code Best Practices — Reference

Source: https://code.claude.com/docs/en/best-practices
Companion to [SKILL.md](SKILL.md). Commands, shortcuts, example prompts and config recipes.

**Why it matters:** Claude's context window holds the whole conversation — every message, file read and command output. A single debugging session can consume tens of thousands of tokens, and performance degrades as it fills. Most practices below follow from that.

---

## 1. Verification

Give Claude a check it can run. Without one, "looks done" is the only signal and you become the verification loop.

| Strategy | Before | After |
|---|---|---|
| Provide verification criteria | *"implement a function that validates email addresses"* | *"write a validateEmail function. example test cases: user@example.com is true, invalid is false, user@.com is false. run the tests after implementing"* |
| Verify UI changes visually | *"make the dashboard look better"* | *"[paste screenshot] implement this design. take a screenshot of the result and compare it to the original. list differences and fix them"* |
| Address root causes | *"the build is failing"* | *"the build fails with this error: [paste error]. fix it and verify the build succeeds. address the root cause, don't suppress the error"* |

How hard the check gates the stop (more setup = less attention needed):

1. **In one prompt** — ask Claude to run the check and iterate. Works on any task.
2. **Across a session** — a [`/goal`](https://code.claude.com/docs/en/goal) condition. A separate evaluator re-checks after every turn; if Claude stalls, the run eventually stops with the goal still set.
3. **Deterministic gate** — a [Stop hook](https://code.claude.com/docs/en/hooks#stop) runs your check as a script and blocks the turn from ending until it passes (there's a cap on consecutive blocks).
4. **Second opinion** — a [verification subagent](https://code.claude.com/docs/en/sub-agents) or [dynamic workflow](https://code.claude.com/docs/en/workflows), so the agent doing the work isn't the one grading it.

After Claude's check passes, run `/verify` yourself to confirm against the running app.

Ask for evidence, not assertions: the test output, the command and its result, or a screenshot.

---

## 2. Explore → Plan → Implement → Commit

Plan when you're uncertain about the approach, the change touches multiple files, or the code is unfamiliar. If you could describe the diff in one sentence, skip the plan.

1. **Explore.** Enter plan mode with `Shift+Tab` until the status bar shows `⏸ plan mode on`, or start with `claude --permission-mode plan`. Claude reads files without changing anything.
   ```text
   read /src/auth and understand how we handle sessions and login.
   also look at how we manage environment variables for secrets.
   ```
2. **Plan.** Press `Ctrl+G` to edit the plan in your text editor before Claude proceeds.
   ```text
   I want to add Google OAuth. What files need to change?
   What's the session flow? Create a plan.
   ```
3. **Implement.** Approve the plan or press `Shift+Tab` to leave plan mode.
   ```text
   implement the OAuth flow from your plan. write tests for the
   callback handler, run the test suite and fix any failures.
   ```
4. **Commit.**
   ```text
   commit with a descriptive message and open a PR
   ```

### Let Claude interview you

For larger features, start with a minimal prompt and let Claude interview you. Replace `[brief description]`:

```text
I want to build [brief description]. Interview me in detail using the AskUserQuestion tool.

Ask about technical implementation, UI/UX, edge cases, concerns, and tradeoffs. Don't ask obvious questions, dig into the hard parts I might not have considered.

Keep interviewing until we've covered everything, then write a complete spec to SPEC.md.
```

Then start a **fresh session** to implement it. The best specs are self-contained: they name the files and interfaces involved, state what is out of scope, and end with an end-to-end verification step. Time spent making the spec precise pays off more than time spent watching the implementation.

---

## 3. Writing prompts

| Strategy | Before | After |
|---|---|---|
| **Scope the task** — which file, what scenario, testing preferences | *"add tests for foo.py"* | *"write a test for foo.py covering the edge case where the user is logged out. avoid mocks."* |
| **Point to sources** | *"why does ExecutionFactory have such a weird api?"* | *"look through ExecutionFactory's git history and summarize how its api came to be"* |
| **Reference existing patterns** | *"add a calendar widget"* | *"look at how existing widgets are implemented on the home page to understand the patterns. HotDogWidget.php is a good example. follow the pattern to implement a new calendar widget that lets the user select a month and paginate forwards/backwards to pick a year. build from scratch without libraries other than the ones already used in the codebase."* |
| **Describe the symptom** — symptom, likely location, what "fixed" looks like | *"fix the login bug"* | *"users report that login fails after session timeout. check the auth flow in src/auth/, especially token refresh. write a failing test that reproduces the issue, then fix it"* |

Vague prompts are useful when you're exploring and can afford to course-correct, e.g. *"what would you improve in this file?"*

### Provide rich content
- **`@path/to/file`** — Claude reads the file before responding.
- **Images** — paste or drag and drop.
- **URLs** — for docs and API references. Allowlist frequent domains with `/permissions`.
- **Pipe data** — `cat error.log | claude -p "explain this error"`.
- **Let Claude fetch it** — via Bash commands, MCP tools, or reading files.

### Ask codebase questions
Good for onboarding — no special prompting required:
- How does logging work?
- How do I make a new API endpoint?
- What does `async move { ... }` do on line 134 of `foo.rs`?
- What edge cases does `CustomerOnboardingFlowImpl` handle?
- Why does this code call `foo()` instead of `bar()` on line 333?

---

## 4. Configuring your environment

### Choosing a mechanism

| Need | Use |
|---|---|
| Broad rules that apply to every session | `CLAUDE.md` — keep it short |
| Domain knowledge or workflows needed only sometimes | Skill: `.claude/skills/<name>/SKILL.md` — loaded on demand |
| Must happen every time, zero exceptions | Hook in `.claude/settings.json` — deterministic, unlike advisory CLAUDE.md |
| Isolated, specialized tasks (review, research) | Subagent: `.claude/agents/<name>.md` — own context and tools |
| External systems (issue trackers, databases, Figma) | MCP server, or a CLI tool |
| Fewer permission prompts | Allowlist, sandbox, auto mode |
| Bundled skills, hooks, agents and MCP servers | Plugin |

See [Extend Claude Code](https://code.claude.com/docs/en/features-overview#match-features-to-your-goal) for more.

### CLAUDE.md

Read at the start of every conversation. Run `/init` to generate a starter, then refine. Run `/context` to confirm it loaded.

**For each line ask: "Would removing this cause Claude to make mistakes?" If not, cut it.** Bloated files cause Claude to ignore your actual instructions.

| ✅ Include | ❌ Exclude |
|---|---|
| Bash commands Claude can't guess | Anything Claude can figure out by reading code |
| Code style rules that differ from defaults | Standard language conventions Claude already knows |
| Testing instructions and preferred test runners | Detailed API documentation (link to docs instead) |
| Repository etiquette (branch naming, PR conventions) | Information that changes frequently |
| Architectural decisions specific to your project | Long explanations or tutorials |
| Developer environment quirks (required env vars) | File-by-file descriptions of the codebase |
| Common gotchas or non-obvious behaviors | Self-evident practices like "write clean code" |

Example:

```markdown
# Code style
- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible (eg. import { foo } from 'bar')

# Workflow
- Be sure to typecheck when you're done making a series of code changes
- Prefer running single tests, and not the whole test suite, for performance
```

Maintaining it:
- If Claude keeps ignoring a rule, the file is probably too long and the rule is getting lost.
- If Claude asks questions the file already answers, the phrasing is probably ambiguous.
- If Claude keeps skipping one instruction, add `IMPORTANT` to that line alone. Emphasizing many lines makes none stand out.
- If Claude already does something correctly without a rule, delete the rule or turn it into a hook.
- Treat it like code: check it into git, review it when things go wrong, prune regularly, and test that behavior actually changes.
- For a checked-in CLAUDE.md, `/doctor` proposes cuts for content Claude can derive from the codebase.
- Import other files with `@path/to/import`. See [CLAUDE.md files](https://code.claude.com/docs/en/memory#claude-md-files).
- Customize compaction, e.g. *"When compacting, always preserve the full list of modified files and any test commands"*.

### Permissions

See [permission modes](https://code.claude.com/docs/en/permission-modes) for current defaults.

- **Auto mode** — a classifier model reviews actions and blocks only what looks risky: scope escalation, unknown infrastructure, or hostile-content-driven actions.
- **Manual mode** — Claude asks before actions that might modify your system (file writes, Bash commands, MCP tools). Safe, but after the tenth approval you're clicking through rather than reviewing.
- **Allowlists** (`/permissions`) — pre-approve tools you know are safe, like `npm run lint` or `git commit`.
- **Sandboxing** (`/sandbox`) — OS-level isolation of filesystem and network access; sandboxed commands run without asking.

Allowlists and sandboxing apply in both manual and auto mode.

### CLI tools

The most context-efficient way to reach external services. Install `gh` — Claude uses it to create issues, open pull requests and read comments; unauthenticated GitHub API requests often hit rate limits. To teach Claude an unknown tool:

```text
Use 'foo-cli-tool --help' to learn about foo tool, then use it to solve A, B, C.
```

### MCP servers

Connect issue trackers, databases, monitoring, Figma, and workflow automation:

```bash
claude mcp add --transport http notion https://mcp.notion.com/mcp
```

### Hooks

Deterministic scripts at fixed points in Claude's workflow — they guarantee the action happens. Claude can write them for you:

- *"Write a hook that runs eslint after every file edit"*
- *"Write a hook that blocks writes to the migrations folder."*

Configure in `.claude/settings.json`; browse with `/hooks`.

### Skills

Claude applies skills automatically when relevant, or you invoke one with `/skill-name`.

Knowledge skill — file `.claude/skills/api-conventions/SKILL.md`:

```markdown
---
name: api-conventions
description: REST API design conventions for our services
---
# API Conventions
- Use kebab-case for URL paths
- Use camelCase for JSON properties
- Always include pagination for list endpoints
- Version APIs in the URL path (/v1/, /v2/)
```

Workflow skill — file `.claude/skills/fix-issue/SKILL.md`, invoked with `/fix-issue 1234`:

```markdown
---
name: fix-issue
description: Fix a GitHub issue
disable-model-invocation: true
---
Analyze and fix the GitHub issue: $ARGUMENTS.

1. Use `gh issue view` to get the issue details
2. Understand the problem described in the issue
3. Search the codebase for relevant files
4. Implement the necessary changes to fix the issue
5. Write and run tests to verify the fix
6. Ensure code passes linting and type checking
7. Create a descriptive commit message
8. Push and create a PR
```

Use `disable-model-invocation: true` for workflows with side effects that you want to trigger manually.

### Subagents

Run in their own context with their own tools. File `.claude/agents/security-reviewer.md`:

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---
You are a senior security engineer. Review code for:
- Injection vulnerabilities (SQL, XSS, command injection)
- Authentication and authorization flaws
- Secrets or credentials in code
- Insecure data handling

Provide specific line references and suggested fixes.
```

Invoke explicitly: *"Use a subagent to review this code for security issues."*

### Plugins

Run `/plugin` to browse the marketplace. For typed languages, install a [code intelligence plugin](https://code.claude.com/docs/en/plugins/code-intelligence) for precise symbol navigation and automatic error detection after edits.

---

## 5. Managing your session

| Action | How |
|---|---|
| Stop mid-action, keep context | `Esc` |
| Restore conversation, code, or both | `Esc Esc` or `/rewind` |
| Condense later messages, keep earlier ones | `/rewind` → pick a checkpoint → **Summarize from here** |
| Condense earlier messages, keep recent ones | `/rewind` → pick a checkpoint → **Summarize up to here** |
| Revert Claude's changes | *"Undo that"* |
| Reset context between unrelated tasks | `/clear` |
| Compact with a focus | `/compact Focus on the API changes` |
| Ask a side question without growing context | `/btw` |
| Name a session (treat it like a branch) | `/rename oauth-migration` |
| Resume the last session / pick from a list | `claude --continue` / `claude --resume` |

- **Auto-compaction:** near the context limit, Claude Code compacts history automatically, keeping code patterns, file states and key decisions.
- **Course-correct early.** If you've corrected Claude more than twice on the same issue, `/clear` and start over with a more specific prompt. A clean session with a better prompt almost always beats a long one full of corrections.
- **Checkpoints:** Claude snapshots files before each change, and every prompt that starts a turn creates a checkpoint. They're saved with the conversation, so you can close the terminal and still rewind — which makes it safe to try something risky. **They only track edits made through Claude's file tools, not Bash commands or external processes. Not a replacement for git.**
- **Subagents for investigation:** *"Use subagents to investigate how our authentication system handles token refresh, and whether we have any existing OAuth utilities I should reuse."* They explore in a separate context and report back a summary.
- Conversations are saved locally, so multi-sitting tasks don't need re-explaining.
- Track context usage with a [custom status line](https://code.claude.com/docs/en/statusline).

---

## 6. Automate and scale

### Non-interactive mode

```bash
# One-off query, plain text
claude -p "Explain what this project does"

# Single JSON object with a `result` field
claude -p "List all API endpoints" --output-format json

# One JSON object per line, starting with an init event
claude -p "Analyze this log file" --output-format stream-json --verbose

# Pipelines
claude -p "<your prompt>" --output-format json | your_command
```

Runs still create a resumable session unless you pass `--no-session-persistence`. Use in CI, pre-commit hooks, and scripts.

### Parallel sessions

- **[Worktrees](https://code.claude.com/docs/en/worktrees)** — separate sessions in isolated git checkouts, so edits don't collide.
- **[Cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging)** — sessions you run pass findings to each other.
- **[Desktop app](https://code.claude.com/docs/en/desktop)** — manage multiple local sessions visually, optionally each in its own worktree.
- **[Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web)** — sessions on Anthropic-managed infrastructure.
- **[Agent view](https://code.claude.com/docs/en/agent-view)** (research preview) — `claude agents` dispatches background sessions you watch from one screen.
- **[Agent teams](https://code.claude.com/docs/en/agent-teams)** (experimental, off by default) — automated coordination with shared tasks, messaging and a team lead.

#### Writer/Reviewer pattern

A fresh session reviews better because it isn't biased toward code it just wrote.

1. **Session A (Writer)** implements:
   ```text
   Implement a rate limiter for our API endpoints
   ```
2. **Session B (Reviewer)** reviews in a clean context:
   ```text
   Review the rate limiter implementation in @src/middleware/rateLimiter.ts.
   Look for edge cases, race conditions, and consistency with our existing
   middleware patterns.
   ```
3. **Session A (Writer)** applies the feedback:
   ```text
   Here's the review feedback: [Session B output]. Address these issues.
   ```

The same works for tests: one Claude writes tests, another writes code to pass them.

### Fan out across files

**Built in:** `/batch <instruction>` splits the change across 5–30 subagents, each in its own worktree.

**Scripted:**

1. Generate a task list:
   ```text
   list all 2,000 Python files that need migrating and save the list to files.txt
   ```
2. Loop over it:
   ```bash
   for file in $(cat files.txt); do
     claude -p "Migrate $file from Python 2 to Python 3. Return OK or FAIL." \
       --allowedTools "Edit,Bash(git commit *)"
   done
   ```
3. Test on 2–3 files, refine the prompt, then run the full set. `--allowedTools` matters when running unattended.

### Auto mode, unattended

```bash
claude --permission-mode auto -p "fix all lint errors"
```

If the classifier repeatedly blocks actions in a `-p` run, the run isn't stopped — see [when auto mode falls back](https://code.claude.com/docs/en/permission-modes#when-auto-mode-falls-back).

### Adversarial review

The longer Claude works unattended, the more an independent check matters. A reviewer subagent sees only the diff and your criteria, not the reasoning that produced it — and the implementing session receives the gaps directly, so you don't copy findings between windows.

- **Correctness:** `/code-review` reviews the current diff in a fresh subagent.
- **Against a plan:**
  ```text
  Use a subagent to review the rate limiter diff against PLAN.md. Check that
  every requirement is implemented, the listed edge cases have tests, and
  nothing outside the task's scope changed. Report gaps, not style preferences.
  ```

A reviewer asked to find gaps will usually report some, even when the work is sound. Chasing every finding leads to over-engineering. Tell the reviewer to flag only gaps that affect correctness or the stated requirements.

---

## 7. Common failure patterns

| Pattern | What happens | Fix |
|---|---|---|
| Kitchen-sink session | Unrelated tasks fill context with irrelevant information | `/clear` between unrelated tasks |
| Correcting over and over | Context fills with failed approaches | After two failed corrections, `/clear` and write a better initial prompt |
| Over-specified CLAUDE.md | Important rules get lost in the noise | Prune ruthlessly, or convert rules to hooks |
| Trust-then-verify gap | Plausible code that misses edge cases | Always provide verification. If you can't verify it, don't ship it |
| Infinite exploration | Unscoped "investigate" reads hundreds of files | Scope narrowly or use subagents |

## 8. Develop your intuition

These are starting points, not rules. Sometimes let context accumulate (deep in one complex problem), skip planning (exploratory task), or keep a prompt vague (to see how Claude interprets it). When Claude does well, notice what you did. When it struggles, ask: was the context too noisy, the prompt too vague, or the task too big for one pass?

## Related docs
- [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- [Extend Claude Code](https://code.claude.com/docs/en/features-overview)
- [Common workflows](https://code.claude.com/docs/en/common-workflows)
- [CLAUDE.md / memory](https://code.claude.com/docs/en/memory)
- [Context window walkthrough](https://code.claude.com/docs/en/context-window)
- [Reduce token usage](https://code.claude.com/docs/en/costs#reduce-token-usage)
