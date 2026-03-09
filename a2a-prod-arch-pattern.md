Good question. The coordinator does not always need to ask an LLM. In most production systems, the coordinator decides in three possible ways, ordered from most reliable → most flexible.

⸻

1. Deterministic Routing (Most Common in Production)

The coordinator maps intent → capability → agent using rules.

Example flow:

User request
   ↓
Intent detection
   ↓
Capability selection
   ↓
Registry lookup
   ↓
Agent call

Example rule table:

Intent	Capability
product price	price_lookup
inventory check	inventory_lookup
product review	review_analysis

Then:

capability = "price_lookup"

agents = registry.find(capability)

call agent

Implementation Example

String capability = intentCapabilityMap.get(intent);

List<AgentInfo> agents =
        registry.findByCapability(capability);

AgentInfo selected = loadBalancer.pick(agents);

callAgent(selected);

Advantages:
	•	deterministic
	•	debuggable
	•	fast
	•	safe

This is the default pattern in serious systems.

⸻

2. Policy / Heuristic Selection

Sometimes multiple agents share the same capability.

Example:

capability: research

Agents:

web-research-agent
academic-research-agent
news-research-agent

Coordinator chooses using heuristics:

Example policies:

latency
cost
success rate
specialization

Example logic:

AgentInfo selected =
    agents.stream()
          .min(Comparator.comparing(AgentInfo::latency))
          .get();

Or simple weighted routing.

This keeps the system predictable.

⸻

3. LLM Tool Selection (Only When Needed)

The coordinator can ask an LLM which capability to use when the task is ambiguous.

Example user prompt:

"Find academic papers about lithium battery recycling"

The coordinator sends the list of capabilities to the LLM.

Prompt:

Available capabilities:

- web_search
- academic_search
- news_search
- summarize_document

User request:
"Find academic papers about lithium battery recycling"

Which capability should be used?

LLM response:

academic_search

Then:

agents = registry.find("academic_search")
call agent

Important:
The LLM selects the capability, not the agent.

Agent selection should stay deterministic.

⸻

4. Why You Should NOT Let LLM Choose the Agent

Bad pattern:

LLM decides:
   call agent A

Problems:
	•	nondeterministic
	•	fragile
	•	debugging nightmare
	•	cannot enforce policies
	•	cannot load balance

Correct architecture:

LLM → capability
Coordinator → agent


⸻

5. Production Architecture Pattern

Best practice pipeline:

User Request
     ↓
Intent Detection (LLM or classifier)
     ↓
Capability Selection
     ↓
Agent Registry Lookup
     ↓
Policy Selection
     ↓
Agent Call

Responsibilities:

Component	Role
LLM	interpret request
Coordinator	decide capability
Registry	know agents
Policy	pick agent
Agent	execute task


⸻

6. Example End-to-End Flow

User asks:

"Summarize recent AI chip news"

Coordinator:

1️⃣ Ask LLM:

Which capability?

Capabilities:
- web_search
- news_search
- summarize

LLM returns:

news_search

2️⃣ Coordinator:

agents = registry.find("news_search")

3️⃣ Policy picks:

news-agent-2

4️⃣ Call agent:

POST /tasks
{
 capability: "news_search",
 input: { topic: "AI chips" }
}


⸻

7. When You Don’t Need an LLM At All

In many enterprise systems:

intent classification model

or even:

regex / rules

Example:

if request.contains("price"):
   capability = "price_lookup"

This is much cheaper and faster.

⸻

8. Practical Recommendation

Use this hierarchy:

1 deterministic routing
2 heuristic policy
3 LLM fallback

Not:

LLM everything

That architecture collapses quickly.

⸻

✅ One more architecture trick used in serious A2A systems is something called Capability Graph Routing.

It allows agents to chain tasks automatically without the coordinator orchestrating everything.

If you’d like, I can show:

“How Uber, Shopify and others implement multi-agent task graphs without central orchestration.”
It’s a powerful pattern for large systems.
