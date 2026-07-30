Im building agentic workflows. give 10 things I must know about graph engineering to build best performing agentic workflows. Also give me 10 things I must not do while building agentic workflows.


Read and edited memory
Read and edited memory
Building on the loop/ReAct patterns — graphs are what you reach for when a single loop stops being enough. Here's what actually matters.

10 things to know
1. The state schema is the real API. Design it before any node. Nodes are transitions over shared state; edges are routing decisions. If your state object is a mess, no amount of clever prompting fixes the graph.

2. Reducers are correctness, not convenience. Every state channel needs a defined merge rule — append, overwrite, max, set-union. Without this, parallel branches fanning back in will silently clobber each other.

3. Checkpoint at node boundaries. This is what buys you durability, resume-after-crash, time-travel debugging, and human-in-the-loop. It's the single highest-leverage architectural decision.

4. Nodes must be idempotent, because they will re-run. Retries and resumes replay nodes. Any side effect (email, payment, DB write) needs an idempotency key or a write-after-checkpoint discipline.

5. Cycles need explicit termination pressure. Max iterations, token/cost budget in state, and a no-progress detector. "The model will decide when to stop" is not a termination condition.

6. Route on structured fields, never on prose. Have the model emit a discriminated union or tool call, write it to state, then let a deterministic conditional edge read that field. Regexing "I think we should search" is how graphs rot.

7. Fan-out/fan-in is your main latency lever. Independent subtasks should run as parallel branches in one superstep, not sequential hops. Most slow agent systems are slow because they're accidentally serial.

8. Subgraphs are context isolation. A subgraph gets its own state schema and its own message history; only a compact result crosses the boundary. This is the actual fix for context-window blowup — not summarization hacks.

9. Keep the data plane out of state. Store handles — file paths, blob IDs, row keys — not 200KB of scraped HTML. Checkpointed state should stay small enough to serialize cheaply on every step.

10. Failure is an edge, not an exception. Per-node timeouts, retry policies, fallback edges, and compensation nodes (saga-style rollback). Model the sad path in the graph itself.

10 things not to do
1. Don't build a mega-node with 40 tools. Tool selection accuracy falls off a cliff past ~10–15. Split into subgraphs with narrow tool sets and a router.

2. Don't reach for an agent when a DAG will do. If the control flow is knowable at design time, hardcode it. Agentic control flow is a tax you pay in latency, cost, and nondeterminism.

3. Don't pass the full message history to every node. Each node should receive only the slice it needs. Blanket history-passing is the most common cause of both cost blowup and degraded reasoning.

4. Don't let two parallel branches write the same key without a reducer. You'll get nondeterministic results that only show up under load.

5. Don't perform irreversible side effects before the checkpoint commits. Classic double-send bug on resume.

6. Don't swallow tool errors. Returning a vague "something went wrong" string into context invites the model to hallucinate a recovery. Return structured, specific errors — or route to an error edge.

7. Don't put secrets or credentials in state. Checkpoints get persisted, logged, and replayed. Inject secrets at node runtime from config.

8. Don't rely on a shared free-text scratchpad. It looks flexible and becomes an unparseable, ever-growing dumping ground. Typed channels instead.

9. Don't evaluate only final outputs. Trajectory evals — did it pick the right tool, take the right path, stop at the right time — catch regressions that end-to-end scoring hides. Unit-test nodes in isolation too.

10. Don't ship without per-node tracing. If you can't see which node ran, what state it received, and which edge it took, you're debugging blind. Every node traversal should be a span keyed to a thread ID.

The through-line: push everything you can make deterministic into code, and spend LLM calls only where genuine judgment is required.


