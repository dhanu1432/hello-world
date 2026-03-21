Great question — this is one of the hardest real-world problems in agent design:

Keeping responses coherent, natural, and on-topic while users jump between topics.

Let’s break this into two parts:
	1.	What techniques top AI agents use
	2.	How you can implement them in Java (Spring/Embabel style)

⸻

Part 1 — Standard Techniques Used in AI Agents

Modern agents (like ChatGPT, Claude, etc.) combine multiple layers, not just one trick.

⸻

1. Conversation State Tracking (Core)

Agents maintain a structured representation of the conversation, not just raw chat history.

Instead of:

User: wifi slow
User: also my bill is wrong

They track:

ActiveTopic: WIFI_TROUBLESHOOTING
SecondaryTopic: BILLING


⸻

Technique
	•	Maintain state machine or session state
	•	Track:
	•	current topic
	•	previous topic
	•	pending tasks

⸻

2. Intent Classification (Fast + Cheap)

Before every response, classify user input:

"my wifi is slow" → WIFI_ISSUE
"why is my bill high" → BILLING


⸻

Algorithms used
	•	Logistic Regression (common in production)
	•	Small Neural Nets (RNN / GRU)
	•	Embedding similarity (cosine similarity)

💡 You’re already doing this (based on your setup).

⸻

3. Topic Segmentation

Detect when the user switches topics.

Example:

Message 1: wifi slow
Message 2: also I can’t make calls

System detects:

Topic shift detected


⸻

Techniques
	•	Embedding similarity threshold
	•	Sliding window comparison

Example:

if similarity(prev, current) < threshold → new topic


⸻

4. Context Window Management

LLMs have limited memory, so agents:
	•	keep relevant context
	•	drop irrelevant context

⸻

Techniques

A. Sliding Window
Keep last N messages

B. Semantic Filtering
Keep only messages related to current topic

C. Summarization
Convert old conversation into summary

⸻

5. Memory Systems (Short-term + Long-term)

Short-term memory

Current conversation

Long-term memory

Stored facts

Example:

User has Fiber plan
User had outage yesterday


⸻

Techniques
	•	Vector DB (RAG)
	•	Key-value memory
	•	Graph memory (advanced systems)

⸻

6. Conversation Graph / State Machine

Instead of linear chat:

A → B → C

Agents use:

Topic1 ↔ Topic2 ↔ Topic3


⸻

Example

WiFi Issue
   ↓
Billing Question
   ↓
Back to WiFi


⸻

7. Response Grounding

Ensure response stays on topic.

⸻

Techniques
	•	Pass only relevant context to LLM
	•	Add system prompts like:

"Answer only about current topic: WIFI"


⸻

8. Tool / Agent Routing (Multi-Agent Systems)

Use different agents per domain:

WifiAgent
BillingAgent
DeviceAgent


⸻

Routing logic

intent → select agent


⸻

9. Relevance Filtering (Very Important)

Before generating response:
	•	filter context
	•	filter memory
	•	filter tools

⸻

Technique

Score relevance:

score = similarity(query, context)

Keep top K.

⸻

10. Dialogue Policies

Rules controlling behavior:

Example:

If topic switch → acknowledge switch
If returning topic → restore context


⸻

⸻

Part 2 — How to Build This in Java (Your Stack)

You’re using:
	•	Spring Boot
	•	Embabel
	•	ONNX classifier
	•	Mongo / vector store

So here’s a production-ready architecture.

⸻

1. Conversation State Object

Create a central object:

class ConversationState {
    String currentTopic;
    String previousTopic;

    Map<String, Object> topicStates; // per-topic data

    List<Message> recentMessages;
}


⸻

2. Intent Classifier (You already have this)

Intent classify(String input);

Example output:

WIFI
BILLING
CALLING


⸻

3. Topic Switch Detection

boolean isTopicSwitch(Intent newIntent, String currentTopic) {
    return !newIntent.equals(currentTopic);
}


⸻

4. Topic State Isolation (CRITICAL)

Store state per topic:

topicStates = {
   "WIFI": WifiState,
   "BILLING": BillingState
}

So when user switches:

restore that topic’s state


⸻

5. Context Builder (Most Important Component)

Before calling LLM:

Context buildContext(ConversationState state, String userInput) {
    return Context.builder()
        .topic(state.currentTopic)
        .recentMessages(filterRelevant(state))
        .memory(fetchRelevantMemory(userInput))
        .build();
}


⸻

6. Relevance Filtering

Use embeddings:

List<Message> filterRelevant(List<Message> messages, String query) {
    return messages.stream()
        .sorted(bySimilarity(query))
        .limit(5)
        .toList();
}


⸻

7. Multi-Agent Routing (Fits Your Embabel Setup)

Agent agent = switch(intent) {
    case WIFI -> wifiAgent;
    case BILLING -> billingAgent;
};


⸻

8. Embabel Integration (Best Pattern)

Use a Supervisor Agent:

@Agent
class SupervisorAgent {

    @Action
    Stage route(UserInput input, ConversationState state) {
        Intent intent = classify(input);

        if (isTopicSwitch(intent, state.currentTopic)) {
            state.previousTopic = state.currentTopic;
            state.currentTopic = intent;
        }

        return switch(intent) {
            case WIFI -> new WifiState(input);
            case BILLING -> new BillingState(input);
        };
    }
}


⸻

9. Memory Integration (RAG)

Before response:

List<Document> docs = vectorStore.search(query);

Inject into context.

⸻

10. Response Guardrails

Add prompt constraints:

You are helping with WIFI issues.
Do not answer billing questions unless explicitly asked.


⸻

11. Advanced (What Top Systems Do)

A. Topic Stack (like browser tabs)

Stack:
[WIFI, BILLING]

User can return to previous topic.

⸻

B. Dialogue Graph

Instead of simple state:

Graph:
WiFi → Router → Signal → Done


⸻

C. Hybrid Memory

Combine:
	•	embeddings
	•	structured state
	•	event logs

⸻

What You Should Implement First (Priority)

Based on your system:

MUST HAVE

✔ Intent classifier (you already have)
✔ Topic state isolation
✔ Context filtering
✔ Supervisor routing

⸻

HIGH IMPACT

✔ Topic switch detection
✔ Per-topic memory
✔ Embedding-based relevance

⸻

ADVANCED

✔ Dialogue graph
✔ Long-term memory
✔ Re-ranking

⸻

Simple Mental Model

User Input
   ↓
Intent Classifier
   ↓
Topic Switch?
   ↓
Select Agent
   ↓
Build Context
   ↓
LLM Response


⸻

Key Insight (Very Important)

Most bad agents fail because:

they send entire conversation to LLM

Good agents:

send only relevant context


⸻

If you want next step

I can design for you:

👉 A full Java class structure (interfaces + implementations)
for a production-grade multi-agent system

OR

👉 Show how to integrate this cleanly with your Embabel + Mongo + ONNX classifier

Both would directly fit your current system.
