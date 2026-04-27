# Harness Engineering — Actionable Items for Agent Developers

*Extracted from: "The Harness Is Everything: What Cursor, Claude Code, and Perplexity Actually Built"*
*Created: April 20, 2026*

---

## Core Thesis

The model is almost irrelevant. The harness is everything. A carefully designed agent environment produced a 64% improvement in benchmark performance from the same model (SWE-agent paper, Princeton NLP). OpenAI shipped 1M lines of code with 3 engineers and zero manually-written code — the bottleneck was always environment design, not model capability.

---

## Environment & Context Design

### 1. Cap search/tool output to prevent context flooding
If a search returns more than ~50 results, suppress the output and return a message telling the agent to narrow its query. This single design decision was one of the highest-leverage changes in the SWE-agent paper (contributed to a 64% performance improvement from the same model). When you flood the context with irrelevant data, every subsequent reasoning step degrades until the context is cleared.

### 2. Build a stateful file viewer that shows ~100 lines at a time with line numbers prepended
Don't dump full files with `cat`. 30 lines loses surrounding context; full files cause the agent to lose track. Line numbers must be readable directly — don't make the agent count. The viewer should maintain position across interactions so the agent doesn't need to re-navigate.

### 3. Implement progressive disclosure for context
Give the agent a short entry point (~100 lines) that points to deeper docs, not a monolithic instruction dump. Anthropic, OpenAI, and SWE-agent all converged on this pattern independently. One big AGENTS.md fails four ways: crowds out task context, makes everything "important" so nothing is, rots instantly, and is hard to verify.

### 4. Collapse old context into single-line summaries
Anything beyond the last ~5 turns should be compressed. Stale observations actively mislead the agent by providing outdated information. Keep the active context focused on recent, relevant information while preserving a compressed record of the overall trajectory.

---

## Feedback Loops & Error Catching

### 5. Integrate a linter into every edit operation
Run a linter after every code edit. If the edit introduces a syntax error, reject it before it's applied and show the agent both the original code and the failed attempt. This was consistently the highest-leverage component in ablation studies — it prevents cascading failures where the agent chases ghost bugs for the rest of its context window.

### 6. Add browser automation (Puppeteer/CDP) for web apps
Agents that can only read code will consistently miss bugs that only manifest at runtime. Anthropic saw a dramatic improvement when agents could navigate the app, click buttons, and verify features end-to-end. The quality of an agent's work is bounded by the quality of its feedback loops.

### 7. Wire observability tools (logs, metrics, traces) into the agent runtime
OpenAI gave Codex access to LogQL, PromQL, and TraceQL on isolated app instances. Agents can debug production-like issues using the same tools a human would, rather than inferring behavior from code alone. Each agent task should run on a fully isolated version of the application with its own observability data.

### 8. Write custom linters with agent-friendly error messages
When a linter catches a violation, the error message should include remediation instructions formatted for injection into agent context. Close the loop: constraint violated → rule stated → fix steps provided, all in one message. This is more effective than a human reviewer catching the same violation days later.

---

## Multi-Session & Long-Running Agent Architecture

### 9. Build an initializer agent that runs first and creates scaffolding
Before any coding agent touches the project, run a separate agent whose only job is to produce three things:
- An `init.sh` script to reliably start the dev environment
- A comprehensive feature list with each item marked pass/fail
- A `progress.txt` file with an initial git commit

This prevents the "try to one-shot everything" and "declare victory too early" failure modes that Anthropic documented.

### 10. Store the feature/task list as JSON, not Markdown
Models are empirically less likely to casually overwrite or rewrite JSON files compared to Markdown. The rigid structure resists casual editing, which is what you want for your ground truth file. Instruct the model to treat this file as inviolable.

### 11. Require every agent session to end with a clean state
Every session must: commit to git with a descriptive message, update the progress file, and leave code in a mergeable state. No half-implemented features left behind. This is non-negotiable for multi-session coherence. Git commits also serve as recovery mechanisms — the agent can revert to the last known-good state when something breaks.

### 12. Implement a standardized startup sequence for every agent session
Before doing any work, execute in order:
1. `pwd` to confirm working directory
2. Read progress file and git log to understand recent work
3. Read feature list and pick highest-priority incomplete item
4. Run `init.sh` to start the dev environment
5. Run basic end-to-end test to verify working state

If the app is broken, fix existing breakage before starting new work. Never build on a broken foundation.

### 13. Make the repository the sole system of record
Anything in Slack, Google Docs, or someone's head is invisible to the agent. Specs, architecture decisions, constraints, and conventions must live as machine-readable files in the repo. Documentation is now the mechanism through which human intent becomes legible to agents. If the agent cannot read it from the repo, it does not exist.

---

## Architecture Enforcement & Code Quality

### 14. Enforce architectural invariants mechanically, not through code review
Human review doesn't scale at agent throughput (3.5+ PRs per engineer per day). Build structural tests and custom linters that enforce dependency directions, boundary crossing rules, and naming conventions. The key principle: enforce boundaries while allowing significant freedom within them. Don't dictate implementations — enforce the foundation.

### 15. Run recurring cleanup background tasks
Scan for deviations from golden principles, update quality grades, and open targeted refactoring PRs. Most should be reviewable in under a minute and auto-mergeable. Encode opinionated mechanical rules that keep the codebase legible for future agent runs.

---

## Orchestration & Parallelism

### 16. Isolate every agent task in its own git worktree
One agent, one worktree. Parallel agents sharing a workspace will conflict. Each agent gets its own working directory, branch, and environment. Changes are validated in isolation before merging. This is how modern CI/CD works for humans and it's exactly the right model for agents.

### 17. Make the application bootable per git worktree
Each agent instance should be able to launch and drive an isolated copy of the app for its own task. Wire Chrome DevTools Protocol into the agent runtime for DOM snapshots, screenshots, and browser navigation. Tear down the isolated instance when the task is complete.

### 18. Shift to a minimal-blocking merge philosophy
At agent-scale throughput, PRs waiting for review block agent work. Keep PRs short-lived, address test flakes with follow-up runs rather than blocking progress. Corrections are cheap; waiting is expensive. This tradeoff looks irresponsible in a low-throughput environment and obvious in a high-throughput one.

---

## Spec & Planning Layer

### 19. Build or adopt spec tooling that inverts the conversation
Instead of humans writing detailed spec tickets (which they're bad at), let the AI propose task DAGs and elaborate requirements, with humans in a verification/approval role before execution begins. The AI is better at generating complete specifications from partial intent than humans are at writing them from scratch.

---

## Diagnostic Mindset

### 20. When something fails, run an environment audit, not a prompt rewrite
Ask these questions in order:
1. What information does the agent need that it can't access?
2. What feedback loop is missing that would catch this mistake before it propagates?
3. Where is context getting polluted with irrelevant information?
4. What constraint relies on agent judgment that should be mechanical?

Each answer points to a specific harness improvement that prevents a *category* of failures, not just one instance. Investing in a better prompt is local and temporary. Investing in a better tool is general and permanent.

---

## Application to Trading Bot Development

These harness principles map directly to building reliable trading bots:

- **Progress files** → Bot state surviving across restarts and crashes
- **Feedback loops** → Catching bad trades before they compound (linter = risk engine)
- **Mechanical constraints** → Drawdown limits, Kelly caps, and kill switches enforced in code, not left to agent judgment
- **Context management** → Keeping the agent focused on current market state, not flooded with stale historical data
- **Clean state requirements** → Every trading session ending with positions logged, P&L recorded, and state documented
- **Observability** → Real-time dashboards showing what the bot sees, what it decided, and why

The difference between "it works in testing" and "it runs reliably 24/7" is the harness.

---

*Source article: "The Harness Is Everything: What Cursor, Claude Code, and Perplexity Actually Built"*
