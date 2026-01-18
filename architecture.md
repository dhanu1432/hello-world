# Kilocode Agent Architecture Analysis

This document provides a detailed overview of the Kilocode agent architecture, based on an analysis of the codebase. It traces the flow from user input to agent execution and identifies the key modules involved.

## High-Level Overview

Kilocode is a VS Code extension that implements an autonomous coding agent. It uses a **Client-Server-like architecture** where the VS Code extension acts as the client (handling UI and state) and the "Agent" (encapsulated in [Task](cci:2://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:180:0-4876:1) or [AgentSession](cci:1://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/kilocode/agent-manager/AgentManagerProvider.ts:881:1-907:2)) acts as the worker, interacting with Large Language Models (LLMs) and executing tools.

There are two distinct modes of operation:

1.  **Native Agent (Sidebar):** The primary mode where the agent runs within the VS Code extension host process.
2.  **CLI Agent (Agent Manager):** A separate mode where agents run as independent CLI processes ([kilocode](cci:1://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:1171:1-1179:2) CLI), orchestrated by the extension.

## Key Modules & Files

### 1. Entry Point & Orchestration

- **[src/extension.ts](cci:7://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/extension.ts:0:0-0:0)**: The main entry point. It initializes [ClineProvider](cci:2://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/webview/ClineProvider.ts:143:0-4050:1), [AgentManagerProvider](cci:2://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/kilocode/agent-manager/AgentManagerProvider.ts:53:0-1903:1), and other core services (`TelemetryService`, [CodeIndexManager](cci:1://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/webview/ClineProvider.ts:2928:1-2934:2), etc.) upon extension activation. It also registers VS Code commands and handles settings migration.

### 2. Native Agent Core

- **[src/core/webview/ClineProvider.ts](cci:7://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/webview/ClineProvider.ts:0:0-0:0)**:
  - **Role:** The brain of the sidebar UI. It implements `vscode.WebviewViewProvider`.
  - **Responsibilities:**
    - Manages the React-based webview UI.
    - Handles user messages from the frontend.
    - Manages a stack of [Task](cci:2://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:180:0-4876:1) instances (`clineStack`), allowing for recursive task delegation.
    - Orchestrates configuration (API providers, MCP servers, etc.).
- **[src/core/task/Task.ts](cci:7://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:0:0-0:0)**:
  - **Role:** The unit of execution for a single agent session.
  - **Responsibilities:**
    - Maintains the conversation history (both UI messages and API messages).
    - **Main Loop ([recursivelyMakeClineRequests](cci:1://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:2487:1-3756:2)):** Handles the core loop of:
      1.  Constructing the prompt (context, environment details, file mentions).
      2.  Sending the request to the LLM (via [ApiHandler](cci:1://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/webview/ClineProvider.ts:1435:1-1479:2)).
      3.  Streaming and parsing the response (text, reasoning, tool calls).
      4.  Executing tools (files, terminal, browser, MCP).
      5.  Feeding results back to the LLM.
    - Manages context window and checkpoints.

### 3. CLI Agent Core

- **[src/core/kilocode/agent-manager/AgentManagerProvider.ts](cci:7://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/kilocode/agent-manager/AgentManagerProvider.ts:0:0-0:0)**:
  - **Role:** manager for the "Agent Manager" panel.
  - **Responsibilities:**
    - Spawns and manages external [kilocode](cci:1://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:1171:1-1179:2) CLI processes using `CliProcessHandler`.
    - Supports parallel execution and "multi-version" modes (using Git worktrees).
    - Bridges communication between the CLI process and the VS Code UI.

### 4. Prompt Engineering

- **[src/core/prompts/system.ts](cci:7://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/prompts/system.ts:0:0-0:0)**:
  - Generates the system prompt sent to the LLM.
  - Dynamically includes:
    - Role definition (based on "modes" like Architect, Ask, Code).
    - Tool definitions (XML or Native protocol).
    - Capabilities (MCP servers, computer use).
    - Context (open files, environment info).

## Execution Flow: User Prompt to Action

### Scenario: Native Sidebar Task

1.  **User Input:** The user types a request in the sidebar webview.
2.  **Message Handling:** The message is sent to [ClineProvider](cci:2://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/webview/ClineProvider.ts:143:0-4050:1), which routes it to the active [Task](cci:2://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:180:0-4876:1) instance (or creates a new one via [createTask](cci:1://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/webview/ClineProvider.ts:3040:1-3136:2)).
3.  **Prompt Construction ([Task.ts](cci:7://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:0:0-0:0)):**
    - The [Task](cci:2://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:180:0-4876:1) gathers context: open files, selected code, terminal output, and "Environment Details".
    - It calls `processKiloUserContentMentions` to resolve references (e.g., `@file`).
4.  **LLM Request ([Task.ts](cci:7://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:0:0-0:0) -> [ApiHandler](cci:1://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/webview/ClineProvider.ts:1435:1-1479:2)):**
    - The [Task](cci:2://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:180:0-4876:1) initiates a streaming request to the configured LLM provider (Anthropic, OpenAI, etc.).
    - It respects rate limits and token usage tracking.
5.  **Response Processing ([Task.ts](cci:7://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:0:0-0:0)):**
    - The [recursivelyMakeClineRequests](cci:1://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:2487:1-3756:2) method processes the stream.
    - **NativeToolCallParser** (or legacy XML parser) identifies tool calls in real-time.
    - Content is incrementally sent to the UI via `presentAssistantMessage`.
6.  **Tool Execution:**
    - Once a tool call is identified and validated (sometimes requiring user approval), it is executed.
    - Tools include: `read_file`, `write_to_file`, `execute_command`, `browser_action`, etc.
7.  **Feedback Loop:**
    - The result of the tool execution is added to the conversation history as a formatted user message (Tool Result).
    - The loop repeats: the updated history is sent back to the LLM for the next step.

### Scenario: CLI Agent Task

1.  **Initialization:** User uses the "Agent Manager" UI to start a session.
2.  **Process Spawning:** [AgentManagerProvider](cci:2://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/kilocode/agent-manager/AgentManagerProvider.ts:53:0-1903:1) uses `CliProcessHandler` to spawn a [kilocode](cci:1://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:1171:1-1179:2) CLI process.
3.  **Communication:**
    - Input is sent via stdin/IPC.
    - Output (events) is captured from stdout/stderr.
4.  **Handling:** The `KilocodeEventProcessor` parses these events (e.g., "thinking", "tool_use") and updates the UI state. The actual intelligence runs in the independent CLI process, likely sharing similar logic to [Task.ts](cci:7://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:0:0-0:0) but packaged for CLI.

## Key Architecture Traits

- **Monorepo:** The logic is shared between the extension and potential other packages (like the CLI).
- **Stateful:** [Task](cci:2://file:///Users/dhana/.gemini/antigravity/scratch/kilocode/src/core/task/Task.ts:180:0-4876:1) instances maintain their own state, history, and abort controllers.
- **Protocol Agnostic:** The agent supports both "Native" (function calling) and "XML" (text parsing) protocols for tool usage, adapting to different model capabilities.
- **Extensible:** It integrates with MCP (Model Context Protocol) to easily add new tools server-side.
