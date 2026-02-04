# OpenClaw Multi-Agent Orchestration Analysis

This report details the implementation of multi-agent orchestration in the OpenClaw project, based on codebase analysis.

## Core Architecture Overview

OpenClaw uses a **hierarchical, tool-driven orchestration model**.

- **Main Agent**: The primary interface with the user.
- **Sub-Agents**: Ephemeral agents spawned by the main agent to handle specific tasks.
- **Router**: Determines the initial entry point.
- **Gateway**: Manages session state and inter-agent communication.

## 1. User Input Handling

### Reception & Classification

- **Entry Point**: `src/cli/run-main.ts` (CLI) or the Gateway service.
- **Routing Logic**: `src/routing/resolve-route.ts`
  - Input is classified based on **bindings** (configuration rules mapping channels, accounts, or peers to specific agents).
  - Everything resolves to a `sessionKey` (e.g., `agent:main:discord:12345`).
  - If no specific binding exists, it falls back to a default agent.

### Determination (What to do)

- **Mechanism**: **LLM-driven decision making**.
- **Implementation**: `src/agents/system-prompt.ts`
  - The system prompt constructs a context containing:
    - **User Identity & Time**
    - **Available Tools** (e.g., `read`, `write`, `exec`, `sessions_spawn`)
    - **Available Skills** (summaries of what skills can do)
  - The model decides whether to:
    - Answer directly.
    - Call a standard tool (e.g., `web_search`).
    - **Spawn a sub-agent** (`sessions_spawn`) for complex tasks.
    - **Read a skill definition** (`read` on `SKILL.md`) if a specific skill is needed.

## 2. Orchestration & Agent Selection

### Agent Selection

- **Single vs. Multiple**: The architecture is primarily single-agent per session, but capable of distinct multi-agent collaboration via spawning.
- **Decision**: The main agent decides to involve other agents. This is **not** a central "router" LLM that pre-plans everything; it is an **autonomous delegation** model.
- **Key File**: `src/agents/tools/sessions-spawn-tool.ts`
  - This tool allows the agent to start a _new_ session with a specific task.
  - Arguments: `task` (required), `agentId` (optional, to select a specialist), `model` (optional override).

### Handover (Main -> Sub-agent)

- **Mechanism**: `sessions_spawn` tool execution.
- **Context Passing**:
  - The `task` description is passed explicitly.
  - An `extraSystemPrompt` is generated (`buildSubagentSystemPrompt` in `src/agents/subagent-announce.ts`) which instructs the sub-agent on its role: "You were created to handle: {task}. Complete this task... You are NOT the main agent."
  - The sub-agent runs in its own isolated session (`childSessionKey`).

### Handover (Sub-agent -> Main)

- **Mechanism**: `src/agents/subagent-announce.ts`
- **Flow**:
  1.  The sub-agent completes its work and outputs a final response.
  2.  The orchestration layer (`runSubagentAnnounceFlow`) detects completion.
  3.  It reads the sub-agent's last reply.
  4.  It constructs a **Trigger Message** to the main agent: "A background task '{task}' just completed successfully. Findings: {reply}."
  5.  This message is injected into the main agent's session (conceptually "whispering" the result).
  6.  The main agent then synthesizes this info for the user.

## 3. Skill Management

### Management

- **Location**: `src/agents/skills/workspace.ts`
- **Discovery**: Skills are loaded from the filesystem (`.openclaw/skills` or workspace `skills/`).

### Selection

- **"Pull" Model**: Skills are not automatically "active".
- **Prompting**: The system prompt (`src/agents/system-prompt.ts`) lists available skills (name + description).
- **Execution**:
  - The agent sees the list.
  - If it decides a skill is relevant, it calls the `read` tool on the skill's `SKILL.md` file.
  - It then follows the instructions in that markdown file.
  - This keeps the context window clean by only loading full skill instructions when needed.

## 4. Response Validation & Evaluation

### Technical Validation

- **Implementation**: `src/agents/pi-embedded-runner/run.ts` & `src/agents/pi-embedded-runner/run/attempt.ts`
- **Checks**:
  - **Context Overflow**: Auto-compacts history if the model runs out of context.
  - **Rate Limits/Auth**: Automatically rotates authentication profiles (`sessions.ts` / `auth-profiles.ts`) if one fails.
  - **Tool Errors**: Captures tool failures and feeds them back to the model to retry.

### Qualitative Evaluation

- **Self-Correction**: The agent loop allows the model to see tool errors and try again.
- **Sub-agent Eval**: If a sub-agent fails or times out, the `runSubagentAnnounceFlow` reports `status: "error"` or `"timeout"` to the main agent. The main agent can then decide to apologize to the user or retry.

## 5. Key File Reference

| Component        | File Path                                      | Purpose                                               |
| :--------------- | :--------------------------------------------- | :---------------------------------------------------- |
| **Routing**      | `src/routing/resolve-route.ts`                 | Maps user input/channels to agent sessions.           |
| **Context**      | `src/agents/system-prompt.ts`                  | Constructs the "brain" (system prompt) for the agent. |
| **Loop (Outer)** | `src/agents/pi-embedded-runner/run.ts`         | Manages auth, context window, and retry logic.        |
| **Loop (Inner)** | `src/agents/pi-embedded-runner/run/attempt.ts` | Executes the actual LLM -> Tool cycle.                |
| **Tooling**      | `src/agents/tools/sessions-spawn-tool.ts`      | The mechanism for creating sub-agents.                |
| **Handover**     | `src/agents/subagent-announce.ts`              | Passes results from sub-agent back to main agent.     |
| **Skills**       | `src/agents/skills/workspace.ts`               | Loads and resolves available skills.                  |

## Recommendation for Your Project

To replicate this:

1.  **Don't build a complex "Router Agent"**: Instead, give your main agent a `spawn_agent(task)` tool.
2.  **Use specific System Prompts**: Create a distinct prompt for sub-agents that emphasizes they are ensuring a specific task is done, limiting their scope.
3.  **Implement "Pull" Skills**: List skill descriptions in your prompt, but require the agent to "read" the full instruction set only when they choose to use it.
4.  **Feedback Loop**: Ensure the result of the `spawn_agent` tool acts as a "promise" that resolves with the text output of the sub-agent, so the main agent knows what happened.
