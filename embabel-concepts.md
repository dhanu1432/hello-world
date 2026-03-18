does each agent gets its own blackboard in embabel? or all agents in a sesson share same blackboard?
Fast
View as codemap
Each agent process gets its own blackboard instance in Embabel, but there are mechanisms for sharing state between processes when needed. DefaultAgentPlatform.kt:125-157

Blackboard Creation and Sharing
Individual Agent Processes
When creating an agent process, the platform either:

Uses an existing blackboard if specified in ProcessOptions DefaultAgentPlatform.kt:129-136
Creates a new blackboard via blackboardProvider.createBlackboard() DefaultAgentPlatform.kt:136-138
Each AgentProcess has its own blackboard instance passed to its constructor. AbstractAgentProcess.kt:39-48

Subagent Blackboard Sharing
Subagents receive a spawned blackboard from the parent process: Subagent.kt:239-240

The spawn operation creates a new blackboard but copies all data from the parent: InMemoryBlackboard.kt:38-46

This means:

Subagent can read parent's blackboard data
Objects added by subagent become available to parent after completion
Each operates in its own process context
Context-Based Sharing
For longer-term state sharing across multiple processes, Embabel provides Context:

Contexts persist across multiple agent processes page.adoc:186-194
When starting a process with a contextId, the blackboard is populated with context data DefaultAgentPlatform.kt:139-148
Chat Sessions
Chatbot sessions use a single long-lived AgentProcess per session: page.adoc:13-21

The blackboard maintains state across the entire session
Multiple user messages are handled by the same process and blackboard AgentProcessChatbot.kt:162-167
Notes
The default ContextRepository implementation is in-memory only and doesn't survive server restarts page.adoc:194-195
Blackboards are thread-safe and implement immutable semantics (objects can't be removed, only hidden) Blackboard.kt:108-114
State management with @State classes hides previous state objects but preserves other blackboard contents page.adoc:20-24
Wiki pages you might want to explore:

Architecture Overview (embabel/embabel-agent)

-------------------
==== Context
Embabel offers a way to store longer term state: the `com.embabel.agent.core.Context`.
While a blackboard is tied to a specific agent process, a context can persist across multiple processes.
Contexts are identified by a unique `contextId` string.
When starting an agent process, you can specify a `contextId` in the `ProcessOptions`.
This will populate that process's blackboard with any data stored in the specified context.
NOTE: Context persistence is dependent on the implementation of `com.embabel.agent.spi.ContextRepository`.
The default implementation works only in memory, so does not survive server restarts.

. **Re-plans from the new state** - The planner considers only actions from the new state
4. **Continues execution** - Until a goal is reached or no plan can be found
**Context is preserved** across state transitions - non-state objects (such as user messages, customer data, and conversation history) remain available.
Only state objects are hidden, ensuring that only the current state's actions are considered by the planner.
NOTE: State transitions **hide** previous state objects but do **not clear** the blackboard.
Non-state objects remain available in the new state.
To clear the entire blackboard (e.g., for looping), use `clearBlackboard = true` on the action.
==== When to Use States
----------------------
processId vs contextId
processId is a unique identifier for each AgentProcess instance, created when the process starts and used to track that specific execution. AgentProcess.kt:64-66

contextId is an optional identifier in ProcessOptions that references a Context for persisting state across multiple processes over time. ProcessOptions.kt:191-193 When specified, the context populates the process's blackboard with stored data. DefaultAgentPlatform.kt:139-148

Blackboards and Processes with Subagents
When a main agent calls a subagent:

Agent Processes: 2 processes are created (main + subagent) DefaultAgentPlatform.kt:205-229
Blackboards: 2 blackboards are created
Main agent has its original blackboard
Subagent receives a spawned blackboard that copies all data from the parent Subagent.kt:239-240
The spawn operation creates a new blackboard instance but copies all objects from the parent:

Multi-turn Conversation State Sharing
In multi-turn conversations, the main agent knows what the subagent did through:

Single Long-lived Process: Chatbot sessions use one AgentProcess that persists across the entire conversation

Blackboard Data Flow: When a subagent completes, objects added to its spawned blackboard become available to the parent process page.adoc:1039-1041

Spawn Mechanism: The spawned blackboard ensures bidirectional data sharing:

Subagent can read all parent blackboard data
After completion, parent can access objects added by subagent
This design allows each agent process to have its own isolated blackboard while still enabling controlled state sharing through the spawn mechanism.

Notes
The default ContextRepository implementation is in-memory only and doesn't survive server restarts page.adoc:194-195
Blackboards are thread-safe and implement immutable semantics (objects can't be removed, only hidden) Blackboard.kt:108-114
Wiki pages you might want to explore:

Architecture Overview (embabel/embabel-agent)
---------------------
