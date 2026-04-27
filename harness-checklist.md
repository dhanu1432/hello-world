# Harness Engineering Checklist

*Track your progress implementing harness principles. Check items as you complete them.*

---

## Phase 1: Foundations (Do These First)

### Context & Environment
- [ ] **Cap tool output** — Search/grep results capped at ~50 items; agent told to refine if exceeded
- [ ] **Stateful file viewer** — Shows ~100 lines at a time with line numbers; maintains position across calls
- [ ] **Progressive disclosure** — Short entry-point doc (~100 lines) pointing to deeper sources; no monolithic AGENTS.md
- [ ] **Context compression** — Old turns (beyond last 5) collapsed to single-line summaries automatically

### Feedback Loops
- [ ] **Linter on every edit** — Syntax errors rejected before applied; agent sees original + failed attempt
- [ ] **Agent-friendly error messages** — Custom linters return remediation instructions formatted for agent context

### State Management
- [ ] **Progress file** — Agent reads at session start, writes at session end; documents what was done and current state
- [ ] **Structured task list (JSON)** — Enumerated, verifiable completion criteria; each item has pass/fail status
- [ ] **Git commit every session** — Descriptive message, clean mergeable state, no half-finished work left behind

---

## Phase 2: Multi-Session Architecture

### Initializer Agent
- [ ] **`init.sh` script** — Reliably starts dev/runtime environment; saves tokens in every subsequent session
- [ ] **Feature list as JSON** — Every feature/behavior described with steps and pass/fail field; treated as inviolable
- [ ] **`progress.txt` + initial commit** — Human-readable log of work done; combined with git history for fast orientation

### Session Protocol
- [ ] **Standardized startup sequence** — pwd → read progress → read git log → read task list → pick task → run init.sh → run smoke test
- [ ] **Fix-before-build rule** — If smoke test fails, fix existing breakage before starting new work
- [ ] **Clean state enforcement** — Every session ends with: git commit + progress update + working app state

### Repository as Source of Truth
- [ ] **All specs in the repo** — No critical knowledge lives only in Slack, Docs, or someone's head
- [ ] **Architecture docs indexed** — Top-level map of domains, package layering, dependency directions
- [ ] **Plans as first-class artifacts** — Progress logs and decision records checked into the repo

---

## Phase 3: Quality & Architecture Enforcement

### Mechanical Guardrails
- [ ] **Structural linters** — Enforce dependency directions, boundary crossing rules, naming conventions
- [ ] **Architectural tests** — Validate layer hierarchy and permissible edges automatically
- [ ] **Recurring cleanup tasks** — Background scans for deviations; auto-generate refactoring PRs

### Verification
- [ ] **Browser automation** — Puppeteer/CDP for end-to-end verification of web apps (agent clicks, fills forms, checks UI)
- [ ] **Observability stack** — Logs, metrics, traces (LogQL/PromQL/TraceQL) accessible to the agent
- [ ] **Isolated app instances** — Each agent task runs on its own copy of the app with its own observability data

---

## Phase 4: Orchestration & Scale

### Parallelism
- [ ] **Git worktree isolation** — One agent = one worktree; changes validated in isolation before merge
- [ ] **Per-worktree app boot** — Each agent can launch and drive its own isolated app instance
- [ ] **Minimal-blocking merges** — Short-lived PRs; flakes fixed via follow-up runs, not blocking gates

### Spec & Planning
- [ ] **AI-proposed task DAGs** — AI generates specs from partial intent; human verifies/approves before execution
- [ ] **Inverted conversation flow** — AI elaborates requirements; human stays in verification role

---

## Phase 5: Diagnostic Discipline

### When Things Break (Run This Audit)
- [ ] What information does the agent need that it can't currently access?
- [ ] What feedback loop is missing that would catch this mistake before it propagates?
- [ ] Where is context getting polluted with irrelevant information?
- [ ] What constraint relies on agent judgment that should be enforced mechanically?
- [ ] Is there a tool improvement that prevents a *category* of failures (not just this one)?

---

## Trading Bot Specific Mappings

*How these principles apply to your Polymarket bot:*

- [ ] **Progress file** → Bot state persists across restarts/crashes (positions, P&L, active markets)
- [ ] **Linter = Risk engine** → Every trade intent validated against Kelly caps, drawdown limits, exposure limits before execution
- [ ] **Mechanical constraints** → Kill switch, quarter-Kelly ceiling, per-market caps enforced in code (not agent judgment)
- [ ] **Context management** → Agent focused on current market state; stale historical data compressed or evicted
- [ ] **Clean state** → Every trading session ends with positions logged, P&L recorded, state documented to disk
- [ ] **Observability** → Dashboard showing what the bot sees, what it decided, and why (Grafana/Prometheus)
- [ ] **Feedback loops** → Trade outcomes logged and compared against predictions; Brier score computed; bad models disabled
- [ ] **Git worktree isolation** → Paper-trade and live-trade environments fully isolated; no cross-contamination

---

**Progress: ___/34 items completed**

*Tip: Work through phases in order. Phase 1 gives you 80% of the value. Phases 3-4 matter at scale.*
