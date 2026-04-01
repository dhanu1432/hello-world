Claide code

most people open claude code, type a prompt, wait for the response, type another prompt.
thats like buying a ferrari and only driving it in first gear.
i wanted to understand why some people seem to get 10x more out of claude code than others. so i did what any reasonable person would do: i read the entire source code (when i say I, i mean claude code of course).
11 layers of architecture. thousands of lines. an agent orchestration platform disguised as a terminal chat.
here's what the source code reveals about how to actually use this thing.

1. CLAUDE.md is loaded every single turn. every. single. turn.
this is the highest leverage thing u can do and almost nobody does it properly.
most people either have nothing in their CLAUDE.md file or they wrote the whole bible in it.
the source code shows that claude code reads ur CLAUDE.md files on EVERY query iteration. not at session start. every turn. that means every time u send a message, it re-reads ur instructions.
there's a whole hierarchy:
- ~/.claude/CLAUDE.md — global (ur coding style, preferences)
- ./CLAUDE.md — project level (architecture decisions, conventions)
- .claude/rules/*.md — modular rules
- CLAUDE.local.md — private notes (gitignored)
u get 40,000 characters. that is a LOT. most people use maybe 200.
put ur architecture decisions in there. ur file conventions. ur testing patterns. ur "never do this" rules. the model reads them every single turn. this is the difference between claude code being a generic assistant and claude code being YOUR assistant that knows YOUR codebase.
if u do one thing after reading this, its this.

2. subagents share the prompt cache (parallelism is basically free)
this is the thing that blew my mind.
when claude code forks a subagent, it creates a byte-identical copy of the parent context. the API caches this. so spawning 5 agents to work on different parts of ur codebase costs barely more than 1 agent doing it sequentially.
read that again.
5 agents. same cost as 1. because they all hit the prompt cache.
most people use claude code like a single worker. one task at a time. wait for it to finish. give it the next thing.
the source code literally has three execution models for subagents:
- fork — inherits parent context, cache-optimized
- teammate — separate pane in tmux or iterm, communicates via file-based mailbox
- worktree — gets its own git worktree, isolated branch per agent
u can tell claude code to spin up 5 agents: one doing a security audit, one refactoring the auth module, one writing tests, one updating docs, one fixing bugs. all at the same time. all sharing the cache.
the architecture is BUILT for this. using it single-threaded is criminal.

3. the permission system is designed to be configured, not clicked through
every time claude code asks "allow this action?" and u click yes, that's a failure of configuration, not a feature.
the source code reveals a 5-level settings cascade:

policy > flag > local > project > user

in ~/.claude/settings.json u can set glob patterns for what's always allowed:
json
{
  "permissions": {
    "allow": [
      "Bash(npm *)",
      "Bash(git *)", 
      "Edit(src/**)",
      "Write(src/**)"
    ]
  }
}

there are three permission modes:
- bypass — no permission checks at all (dangerous but fast)
- allowEdits — auto-allows file edits in ur working directory
- auto (this is new) — runs an LLM classifier on each action. this is the sweet spot.
auto mode has its own allow/deny lists u can configure. the source code shows it races multiple resolvers in parallel: user click, hook classifier, bridge, and first one to respond wins.
every time u stop to click "allow" is time wasted. configure it once. never click again.

4. there are 5 compaction strategies. context pressure is a real problem
the source code has FIVE different ways to compress ur conversation when it gets too long:
1. microcompact — time-based clearing of old tool results
2. context collapse — summarizes spans of conversation
3. session memory — extracts key context to a file
4. full compact — summarizes entire history
5. PTL truncation — drops oldest message groups
this tells u something important: context overflow is a central problem the engineers spent a LOT of time on.
what this means for u:
- use `/compact` proactively. don't wait for the system to auto-compact and lose context u care about.
- the default window is 200K tokens. but u can opt into 1M tokens by using the `[1m]` model suffix. for large refactors across many files, this matters.
- long sessions accumulate "session memory" — structured summaries of task specs, file lists, workflow state, errors, and learnings. this is why resuming a session is better than starting fresh.
- large tool results get stored to disk with only an 8KB preview sent to the model. if u paste a massive file, the model may only see a fraction. keep inputs focused.
the people getting the most out of claude code use `/compact` like a manual save point in a video game. preserve what matters, clear what doesn't, keep moving.

5. the hook system is the real extension API  (25+ lifecycle events)
this is the power-user feature that almost nobody knows about.
the source code reveals 25+ lifecycle events u can hook into:
- PreToolUse — runs before any tool executes
- PostToolUse — runs after any tool executes
- UserPromptSubmit — runs when u send a message
- SessionStart / SessionEnd — session lifecycle
- and 20+ more

with 5 types of hooks:
- command — run a shell command
- prompt — inject context via LLM
- agent — run a full agent verification loop
- HTTP — call a webhook
- function — run JS

real examples of what u can do:
- auto-run linting before every file write
- run tests after every edit
- inject relevant docs into every prompt automatically
- send a slack notification when a task completes
- validate that security patterns are followed before code ships

the `UserPromptSubmit` hook is especially crazy. u can inject `additionalContext` into every single message u send. imagine automatically attaching test output, recent git diffs, or project state to every prompt without typing it.
this is how u build a custom development environment on top of claude code. not by prompting better. by hooking into the system itself.

6. sessions are persistent and resumable (stop starting fresh)
every conversation is saved as JSONL at 

~/.claude/projects/{hash}/{sessionId}.jsonl

the source code supports:
- --continue — resume ur last session
- --resume — pick a specific past session  
- --fork-session — branch from a past conversation (i personally love this)
session memory extraction preserves key context across compactions: task specs, file lists, workflow state, errors, and learnings.
most people start a new session every time they open claude code. this is like closing ur IDE and reopening it from scratch every hour. all the context about what u were doing, what failed, what u learned — gone.
use `--continue`. always. let context accumulate. let the session memory build up learnings over time. the source code literally has infrastructure for this. use it.

7. the tool system runs 60+ tools with smart batching
claude code has 60+ built-in tools. but the interesting part is HOW it runs them.
the source code partitions tool calls into two categories:
- concurrent — read-only operations (reading files, searching, globbing) run in parallel
- serial — mutating operations (edits, writes, bash commands) run one at a time
this means when claude code needs to read 10 files to understand ur codebase, it reads all 10 simultaneously. but when it needs to edit 3 files, it does them one at a time to avoid conflicts.
on top of the built-in tools, u can connect MCP servers that add more tools. the source code uses deferred loading. MCP tools only load when needed, so connecting 5 MCP servers doesn't slow down every request.
and there's ToolSearch for deferred discovery of tools the agent doesn't know about yet.
the practical takeaway: if ur workflow involves external systems (databases, cloud providers, CI/CD), connect MCP servers for them. the architecture handles the complexity. u just get more capabilities.

8. the streaming architecture means interruption is cheap
the entire pipeline uses async generators yielding individual events. pressing Escape cleanly aborts the current stream without losing previous context.
this seems small but it changes how u should use claude code.
dont wait for a response u know is going wrong. interrupt immediately and redirect. the source code is designed for this. ur previous context is preserved. the interrupted response is discarded cleanly. zero penalty.
think of it like pair programming. if ur pair starts going down the wrong path, u dont wait for them to finish. u say "actually, go this way instead." same energy.
9. the retry system is more sophisticated than u think**
the source code reveals:
- 10 retries with exponential backoff and jitter (500ms base)
- automatic OAuth token refresh on 401/403
- model fallback: if Opus fails 3 times with 529 errors, it automatically falls back to Sonnet
- 90-second idle watchdog on streams — if streaming stalls, it falls back to non-streaming
- persistent mode has infinite retry with 5-minute max backoff
this means claude code is designed to be left running. it handles API hiccups, rate limits, and outages gracefully. u dont need to babysit it. let it run in the background and come back to results.

the tldr: highest leverage actions from the source code:
• write a real CLAUDE.md → loaded every turn. 40K chars. highest leverage config.
• parallelize with subagents → fork model shares prompt cache. 5 agents ≈ cost of 1.
• configure permissions in settings.json → eliminate click fatigue forever.
• use /compact proactively → 5 compaction strategies exist because context pressure is real.
• set up hooks → 25+ events, 5 types. this is the real extension API.
• always --continue sessions → JSONL persistence + session memory = accumulated context.
• connect MCP servers → deferred loading means zero cost until used.
• interrupt freely → async generators mean zero penalty for redirecting.

the bottom line: claude code is an agent orchestration platform wearing a terminal UI.
the people getting 10x output from it aren't better prompters. they configured it. they parallelized it. they hooked into it. they let context accumulate across sessions.
the source code makes this obvious. now u know what it actually does under the hood.

