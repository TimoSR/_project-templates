# Prompt caching in Claude Code

## Contents

* Mechanism
* What invalidates
* What keeps the cache
* TTL
* Scope
* Checking performance
* Subagents
* Disabling

## Mechanism

* The model has no memory between requests, so every turn re-sends system prompt, project context, all messages and tool results.
* The API matches the **start** of the request (the prefix) against what it recently processed. Exact match only, no per-file caching: a change anywhere recomputes everything after it.

```
turn 2:  [system][ctx][t1][t2-new]       prefix = all of turn 1 → cache read, only t2 processed
turn 4:  [SYSTEM CHANGED][ctx][t1..t3]   prefix differs from byte 0 → full reprocess + rewrite
```

| Layer | Content | Changes when |
|---|---|---|
| System prompt | core instructions, tool definitions | the set of loaded tool definitions changes |
| Project context | CLAUDE.md, auto memory, unscoped rules | session start, `/clear`, `/compact` |
| Conversation | messages, tool results | every turn |

* Each model has its own cache. Effort level is part of the key on most models; on Opus 5.5, Sonnet 5.5 and Fable 5.1 (API key or subscription) changing effort keeps the cache.

## What invalidates

Cost = one slower, more expensive turn, then the new prefix is cached.

| Action | Why |
|---|---|
| `/model` switch | separate cache per model. `opusplan` makes every plan-mode toggle a switch. Auto fallback and a skill's `model:` frontmatter also switch |
| Effort change (most models) | effort is in the cache key |
| First fast-mode turn | header is part of the key; once per conversation. Turn on at session start, not deep in a long one |
| MCP server connect/remove with tools loaded upfront | tool definitions are in the system layer. With tool search (default) the first request's tool list is frozen, so no invalidation |
| Deny rule on a whole tool (`Bash`, `mcp__*`) without tool search | definition removed. Scoped rules like `Bash(rm *)` don't matter |
| `/compact` | new shorter history, new prefix. Cheap while cache is warm (summarize request reads the prefix), costly after a long idle |
| Many images/PDFs | oldest batch dropped when limits hit |
| Upgrading Claude Code | system prompt or tool defs change; shows up on the first turn after restart |

Plugins: skills, commands, agents, hooks, monitors, themes append after the conversation, so they never invalidate. Plugin MCP servers follow the MCP rule.

## What keeps the cache

| Action | Why it's safe |
|---|---|
| Editing repo files | read stays as-is in history; a `<system-reminder>` is appended |
| Editing CLAUDE.md | read once at start and held; **the edit doesn't apply** until `/clear`, `/compact` or restart |
| Nested CLAUDE.md, `paths:` rules | load when first matching file is read; editing before that does take effect |
| Permission mode change | system prompt and tools unchanged |
| Output style switch | delivered as a message (applies next message; before v2.1.251 it waited for `/clear`) |
| Skill / command invocation | injected as a user message |
| `/recap` | appended output, not a replacement |
| `/rewind` | truncates back to an already-cached prefix |
| Spawning a subagent | parent prefix untouched |

## TTL

* Idle entries expire; each hit resets the timer. First turn after a long gap is slow.
* Two TTLs: 5 minutes, and 1 hour (higher cache-write price; pays off for idle-and-return, wastes money on short bursts).

| Request bucket | Subscription, within plan usage | API key, usage credits, cloud provider |
|---|---|---|
| Main conversation (turns, `-p`, SDK) | 1 hour | 5 minutes |
| Everything else (subagents, workflows, teammates, forks, compaction, titles) | 5 minutes | 5 minutes |

Set it yourself (`5m` or `1h`, v2.1.242+):

| Bucket | Setting | Env var |
|---|---|---|
| Main | `promptCacheTtl` | `CLAUDE_CODE_PROMPT_CACHE_TTL` |
| Everything else | `subagentPromptCacheTtl` | `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL` |

Order: `FORCE_PROMPT_CACHING_5M=1` (forces 5m for both) → bucket env var → bucket setting → subagent `experimental.cacheTtl` → `ENABLE_PROMPT_CACHING_1H=1` → default. Past the plan limit (usage credits) the main conversation drops to 5m unless you set it. Verify: `claude -p "hello" --output-format json`, read `usage.cache_creation.ephemeral_1h_input_tokens` vs `_5m_`.

## Scope

* Effectively one machine + one directory: the system prompt embeds auto-memory paths and the working-directory announcement.
* Parallel sessions in the same directory share cache. Sequential sessions share only if the startup git-status snapshot matches.
* Through an LLM gateway: it must forward `cache_control` markers and the `anthropic-beta` header, or history bills as uncached every turn.

## Checking performance

| Field | Meaning |
|---|---|
| `cache_creation_input_tokens` | written this turn (write rate) |
| `cache_read_input_tokens` | served from cache (cheaper rate) |

* High read:creation = healthy. Creation high turn after turn = something in the prefix keeps changing.
* `/usage` shows a `Prompt cache (main)` line: hit ratio, misses, warm/cold, likely cause of the last miss (v2.1.251+, cause text v2.1.260+). A statusline script reads `current_usage` and `prompt_cache`.

## Subagents

* Own system prompt and tools, so the first request misses the parent's cache and warms its own. Gets the 5-minute bucket.
* A **fork** inherits system prompt, tools and history, so its first request reads the parent's cache. Compaction's summarize call and resumed subagents also reuse prefixes.

## Disabling

Set to `1`: `DISABLE_PROMPT_CACHING` (all), `_HAIKU`, `_SONNET`, `_OPUS`, `_FABLE` (the model the alias resolves to; a pinned model ID keeps caching, use the global one). For debugging only.
