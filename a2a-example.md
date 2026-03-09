Below is a practical, production-style example of 5 cooperating agents using an A2A (Agent-to-Agent) architecture. The goal is to show how agents discover each other, delegate tasks, and collaborate to complete a complex request.

This example is intentionally simple enough to implement but realistic enough for production thinking.

⸻

Scenario: AI-Powered Product Intelligence System

User asks:

“Should I buy the new MacBook Air M4? Compare price, reviews, and potential risks.”

The system uses 5 cooperating agents:
	1.	Coordinator Agent (workflow orchestrator)
	2.	Research Agent (collects product information)
	3.	Pricing Agent (price analysis)
	4.	Review Analysis Agent (sentiment + summarization)
	5.	Risk/Compliance Agent (checks issues, recalls, risks)

⸻

Architecture Overview

                   Agent Registry
                         │
         ┌───────────────┼───────────────┐
         │               │               │
   Coordinator      Research        Pricing
       Agent          Agent           Agent
         │               │               │
         │               └───────────────┐
         │                               │
         │                        Review Analysis
         │                               │
         └───────────────► Risk Agent ◄──┘

Transport Layer: HTTP / Kafka / NATS
Task State: Redis/Postgres
Observability: OpenTelemetry

Agents communicate through A2A task messages.

⸻

Step 1: Agent Registry

All agents register their capabilities.

Example registry entry:

{
  "agent_id": "research-agent",
  "capabilities": [
    "product_research",
    "market_info"
  ],
  "endpoint": "http://research-agent.internal"
}

Pricing agent:

{
  "agent_id": "pricing-agent",
  "capabilities": [
    "price_lookup",
    "price_comparison"
  ]
}

Coordinator never hardcodes agent addresses.
It queries the registry.

⸻

Step 2: User Request

User asks the system:

Should I buy MacBook Air M4?

This goes to Coordinator Agent.

Coordinator creates a workflow task:

{
  "task_id": "task-921",
  "type": "product_decision_analysis",
  "input": {
    "product": "MacBook Air M4"
  }
}


⸻

Step 3: Coordinator Delegates Research

Coordinator discovers agent with capability:

product_research

Then sends task:

{
  "task": "product_research",
  "input": {
    "product": "MacBook Air M4"
  }
}

Research Agent performs:
	•	specs lookup
	•	product description
	•	market positioning

Returns:

{
  "status": "completed",
  "result": {
    "cpu": "M4",
    "ram": "16GB",
    "battery": "18 hours",
    "launch_year": 2025
  }
}


⸻

Step 4: Coordinator Requests Pricing Analysis

Coordinator sends task to Pricing Agent.

{
  "task": "price_comparison",
  "input": {
    "product": "MacBook Air M4"
  }
}

Pricing agent:
	•	checks multiple stores
	•	analyzes historical price trends

Returns:

{
  "result": {
    "average_price": 1399,
    "lowest_price": 1299,
    "price_trend": "stable"
  }
}


⸻

Step 5: Review Analysis Agent

Coordinator sends:

{
  "task": "review_analysis",
  "input": {
    "product": "MacBook Air M4"
  }
}

Review agent:
	•	scrapes reviews
	•	performs sentiment analysis
	•	extracts common complaints

Returns:

{
  "result": {
    "positive_sentiment": 0.86,
    "negative_sentiment": 0.14,
    "common_issues": [
      "high price",
      "limited ports"
    ]
  }
}


⸻

Step 6: Risk/Compliance Agent

Coordinator asks:

{
  "task": "product_risk_check",
  "input": {
    "product": "MacBook Air M4"
  }
}

Risk agent checks:
	•	recalls
	•	lawsuits
	•	safety alerts
	•	warranty concerns

Response:

{
  "result": {
    "recalls": false,
    "major_issues": [],
    "risk_score": 0.05
  }
}


⸻

Step 7: Coordinator Synthesizes Results

Coordinator now has results from four agents.

Final prompt to LLM:

Research results
Pricing analysis
Review sentiment
Risk analysis

Generate buying recommendation.

Final output:

Recommendation: Buy

Reasons:
- Strong performance with M4 chip
- Positive review sentiment (86%)
- Stable pricing
- No major risk factors

Consideration:
- Price is relatively high compared to competitors


⸻

A2A Task Lifecycle Example

Every task follows lifecycle:

submitted
accepted
in_progress
completed
failed

Example:

task-921
status: in_progress
assigned_agent: research-agent


⸻

Example A2A API

Agents expose endpoints:

POST /tasks
GET /tasks/{id}
POST /tasks/{id}/events

Task submission example:

{
  "task_id": "task-123",
  "task": "price_lookup",
  "input": {
    "product": "MacBook Air M4"
  }
}


⸻

Message Bus Variant (Recommended at Scale)

Instead of HTTP:

Coordinator → Kafka topic → pricing.tasks

Pricing agent subscribes.

Benefits:
	•	retry
	•	buffering
	•	scaling workers
	•	fault isolation

⸻

Observability Example

Trace looks like:

trace_id: ab12

User Request
  ├ Coordinator Agent
  ├ Research Agent (2.1s)
  ├ Pricing Agent (350ms)
  ├ Review Agent (4.2s)
  └ Risk Agent (180ms)

You can see:
	•	slow agents
	•	failures
	•	cost hotspots

⸻

Security Model

Agents authenticate via:

JWT
mTLS
Service Mesh

Example policy:

review-agent cannot call pricing-agent

Only coordinator can.

⸻

Production Deployment

Typical Kubernetes deployment:

agents
 ├ coordinator-agent
 ├ research-agent
 ├ pricing-agent
 ├ review-agent
 └ risk-agent

infra
 ├ agent-registry
 ├ redis
 ├ kafka
 ├ prometheus
 └ grafana


⸻

Key Design Principle

Agents should be:

stateless
retry-safe
idempotent
capability-driven

Otherwise distributed execution becomes unstable.

⸻

What This Architecture Enables

With A2A you can easily add new agents:

fraud-agent
supply-chain-agent
market-trend-agent

Coordinator automatically discovers them.

System evolves without redesign.

⸻

If you’d like, I can also show something extremely useful when designing agent systems:

“The 6 agent roles that appear in almost every production multi-agent architecture (OpenAI, Google, Anthropic style systems).”

These patterns make systems far more reliable and scalable.
