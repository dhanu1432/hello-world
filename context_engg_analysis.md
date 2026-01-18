# Kilocode Context Management Analysis

This report details how the Kilocode agent manages context, ensuring the LLM has relevant information without exceeding token limits. It identifies specific techniques and code files you can reference for your own project.

## 1. Context Sources: Gathering Information

The agent builds its context from three primary layers: **Static**, **Dynamic (Implicit)**, and **Dynamic (Explicit)**.

### A. Static System Context

**File:** `src/core/prompts/system.ts`

The base system prompt is dynamically assembled but remains relatively static during a task. It includes:

- **Role Definition:** Persona and capabilities (e.g., "Software Engineer").
- **Tool Definitions:** XML or Native format specs for available tools.
- **Capabilities:** Available resources (MCP servers, computer use).

### B. Dynamic Environment Context (Implicit)

**File:** `src/core/environment/getEnvironmentDetails.ts`
**Function:** `getEnvironmentDetails`

This is a critical "grounding" technique. Before every request, the agent gathers the current state of the IDE to prevent hallucinations about the environment.

- **Visible Files:** Lists files currently open and visible in VS Code editors.
- **Open Tabs:** Lists all open tabs (even if not currently focused).
- **Terminal Output:** Captures the last `N` lines of output from active and background terminals. This allows the agent to see build errors or command results without user copy-pasting.
- **Git Status:** Summarizes changed files.
- **Recent Modifications:** Highlights files changed since the agent last read them.

### C. Dynamic User Context (Explicit)

**Files:** `src/core/mentions/processKiloUserContentMentions.ts`, `src/core/mentions/index.ts`

Users can explicitly inject context using "mentions" (e.g., `@file`, `@url`, `@problems`).

- **Parsing:** The system regex-matches tags in user messages.
- **Expansion:** It resolves paths/URLs and injects the full content into the `UserMessage` sent to the LLM.

---

## 2. Context Optimization: Managing Token Limits

Kilocode uses a sophisticated localized strategy to manage the "Context Window" (memory). It prioritizes **condensing** first, then **truncating** as a fallback.

### Technique A: Intelligent Condensation (Summarization)

**Files:**

- `src/core/condense/index.ts` (`summarizeConversation`, `manageContext`)
- `src/core/context-management/index.ts`

**How it works:**

1.  **Threshold Trigger:** When context usage hits a threshold (e.g., 90%).
2.  **Recursive Summary:** An LLM call is made to "Summarize the conversation so far".
3.  **Replacement:** The detailed message history (except the very first and very last few messages) is replaced by a single `AssistantMessage` containing the summary.
4.  **Preservation:** Crucially, it preserves "Tool Use" blocks if they are paired with a recent "Tool Result" to prevent API errors (orphaned tool results).

### Technique B: Sliding Window Truncation (Fallback)

**File:** `src/core/context-management/index.ts` (`truncateConversation`)

**How it works:**

1.  **Logic:** If summarization isn't enough or fails, it "hides" the middle portion of the conversation.
2.  **Non-Destructive:** It doesn't delete messages from the local database. It tags them with `truncationParent`.
3.  **API View:** When constructing the API request, tagged messages are filtered out, effectively creating a sliding window that moves forward, keeping the start (task def) and end (current context).

---

## 3. Context Consistency: Handling Stale Data

### Technique: File Context Tracking

**File:** `src/core/context-tracking/FileContextTracker.ts`

**Problem:** The agent reads a file, then the user edits it externally. The agent's context is now stale.
**Solution:**

1.  **Watchers:** Creates `vscode.FileSystemWatcher` for any file the agent has read or edited.
2.  **State Tracking:** Marks files as `stale` vs `active` in `task_metadata.json`.
3.  **Notification:** If the agent tries to edit a stale file, the system can warn it or force a re-read (often handled in the prompt or tool logic).

---

## 4. RAG (Retrieval-Augmented Generation)

**File:** `src/services/code-index/manager.ts`

**How it works:**

- **Indexing:** Periodically scans the codebase and embeds chunks using an embedding model.
- **Storage:** Uses a local vector store (likely Qdrant/LanceDB based on imports).
- **Retrieval:** When the user asks a broad question, the system searches the vector index and injects relevant snippets into the context (often via the `search_files` tool or implicit context injection).

## Summary: Patterns to Reuse

1.  **Environment Snapshot:** Always prepend the current state (files, distinct errors, terminal tail) to the logical Prompt.
2.  **Two-Stage Management:** Try to _summarize_ old history before you _delete_ it.
3.  **Anchor Points:** Always keep the **First Message** (User's goal) and **Last N Messages** (Immediate context) when truncating.
4.  **Reference Tracking:** Don't just dump text; track _where_ it came from (file paths) and watch those sources for changes.
