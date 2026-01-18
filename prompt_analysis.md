# Kilocode Prompt Token Analysis

This report provides an estimated token count for the various prompt components in the Kilocode agent architecture.
_Estimates are based on a standard heuristic of ~4 characters per token._

## 1. Core System Prompt Sections

These sections are always included (or conditionally included based on basic settings).

| Section                 | Source File                                        | Size (Bytes) | Est. Tokens | Description                                                              |
| :---------------------- | :------------------------------------------------- | :----------- | :---------- | :----------------------------------------------------------------------- |
| **Rules**               | `src/core/prompts/sections/rules.ts`               | ~7,870       | **~1,967**  | Critical operational rules (paths, user interaction, forbidden actions). |
| **Tool Use Guidelines** | `src/core/prompts/sections/tool-use-guidelines.ts` | ~4,965       | **~1,241**  | Instructions on how to reason about and execute tools.                   |
| **Capabilities**        | `src/core/prompts/sections/capabilities.ts`        | ~2,272       | **~568**    | Description of agent capabilities (fs, command execution).               |
| **Objective**           | `src/core/prompts/sections/objective.ts`           | ~2,049       | **~512**    | High-level goal setting and iterative workflow instructions.             |
| **Tool Use (Header)**   | `src/core/prompts/sections/tool-use.ts`            | ~1,877       | **~469**    | Introduction to the tool-use block (XML or Native).                      |
| **Modes**               | `src/core/prompts/sections/modes.ts`               | ~1,601       | **~400**    | Descriptions of available modes (Architect, Code, Ask).                  |
| **System Info**         | `src/core/prompts/sections/system-info.ts`         | ~1,642       | **~410**    | OS, Shell, and Environment details placeholder.                          |

### **Subtotal (Base Context): ~5,567 Tokens**

_(This is the "static" cost before adding any specific tools or user context.)_

---

## 2. Tool Definitions

Tool definitions are injected dynamically based on the active mode (e.g., "Code" mode might have different tools than "Architect" mode).

| Tool                 | Source File                                  | Size (Bytes) | Est. Tokens | Description                                              |
| :------------------- | :------------------------------------------- | :----------- | :---------- | :------------------------------------------------------- |
| **read_file**        | `src/core/prompts/tools/read-file.ts`        | ~3,855       | **~963**    | Instructions for reading files (single/multi-read).      |
| **edit_file**        | `src/core/prompts/tools/edit-file.ts`        | ~3,579       | **~894**    | Complex instructions for diff/replace operations.        |
| **update_todo_list** | `src/core/prompts/tools/update-todo-list.ts` | ~3,097       | **~774**    | Managing the task checklist.                             |
| **browser_action**   | `src/core/prompts/tools/browser-action.ts`   | ~6,353       | **~1,588**  | Heavy tool: Instructions for interacting with a browser. |
| **write_to_file**    | `src/core/prompts/tools/write-to-file.ts`    | ~2,308       | **~577**    | creating new files.                                      |
| **execute_command**  | `src/core/prompts/tools/execute-command.ts`  | ~1,670       | **~417**    | Running CLI commands.                                    |
| **search_files**     | `src/core/prompts/tools/search-files.ts`     | ~1,805       | **~451**    | Regex search.                                            |
| **codebase_search**  | `src/core/prompts/tools/codebase-search.ts`  | ~1,725       | **~431**    | RAG/Semantic search.                                     |

### **Tool Suite Cost (Avg Code Mode): ~4,000 - 6,000 Tokens**

_(Depending on whether browser usage or heavy RAG tools are enabled.)_

---

## 3. Dynamic Context (Variable)

This is highly variable but often the largest part of the prompt.

- **Environment Details:** ~500 - 2,000 Tokens (Open files list, terminal output history).
- **User Messages + History:** 0 - 200,000+ Tokens (Managed by `sliding window` / `condensation`).

## Synthesis: "Sweet Spot" Estimation

For a robust coding agent like Kilocode, the **System Prompt** (Base + Tools) typically consumes:

- **Minimum:** ~8,000 Tokens (Basic tools, no browser/RAG).
- **Typical:** ~10,000 - 12,000 Tokens (Standard coding task).
- **Heavy:** ~15,000+ Tokens (Full browser automation + complex custom tools).

### Recommendation for Your Project

If you are building a similar agent:

1.  **Budget ~10k tokens** for a comprehensive System Prompt.
2.  **Optimize Tool Docs:** As you can see, `read_file` and `browser_action` are huge. If you use a native tool-calling model (like GPT-4o or Claude 3.5 Sonnet), you might not need such verbose XML descriptions, potentially saving ~30-40%.
3.  **Modularize:** Kilocode's "Mode" system allows stripping out unused tools (e.g., removing `browser_action` makes the prompt ~1.5k tokens lighter).
