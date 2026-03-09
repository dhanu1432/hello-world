Below is a clean, production-friendly Spring Boot project structure for an A2A agent platform that includes:
	•	Agent Registry
	•	Coordinator (orchestrator)
	•	Multiple agents
	•	Shared libraries

This structure works well for Spring Boot + Embabel + Mongo + Redis + EKS and scales cleanly when you reach 10–20 agents.

I’ll show:

1️⃣ Overall architecture
2️⃣ Multi-repo vs mono-repo decision
3️⃣ Project layout
4️⃣ Registry service structure
5️⃣ Coordinator service structure
6️⃣ Agent service structure
7️⃣ Shared libraries
8️⃣ Build strategy
9️⃣ Deployment strategy

⸻

1. High-Level Architecture

Your platform will look like this:

                UI / External API
                       │
                       ▼
                Coordinator Service
                       │
         ┌─────────────┼─────────────┐
         │             │             │
   Research Agent   Pricing Agent   Review Agent
         │             │             │
         └─────────────┼─────────────┘
                    Registry
                       │
               Mongo + Redis

Responsibilities:

Component	Responsibility
Registry	agent discovery
Coordinator	workflow orchestration
Agents	task execution
Shared libs	A2A protocol + models


⸻

2. Mono Repo vs Multi Repo

For most teams building agent systems:

Mono repo works best initially.

Example repo:

agent-platform

Inside:

registry-service
coordinator-service
agents
shared-libraries

Why mono repo?
	•	easier refactoring
	•	shared models
	•	consistent protocol
	•	faster development

Large companies sometimes split later.

⸻

3. Top-Level Repository Structure

Clean root layout:

agent-platform
│
├── registry-service
│
├── coordinator-service
│
├── agents
│   ├── research-agent
│   ├── pricing-agent
│   ├── review-agent
│   └── risk-agent
│
├── shared
│   ├── a2a-protocol
│   ├── agent-sdk
│   └── common-models
│
├── infra
│   ├── helm
│   └── terraform
│
└── docs

This separation prevents coupling.

⸻

4. Registry Service Structure

Registry is a simple Spring Boot service.

registry-service
│
├── src/main/java/com/company/registry
│
│   ├── controller
│   │     AgentRegistryController
│   │
│   ├── service
│   │     AgentRegistryService
│   │
│   ├── repository
│   │     AgentRepository
│   │
│   ├── model
│   │     AgentRegistration
│   │
│   └── config
│         RedisConfig
│
├── resources
│
└── RegistryApplication.java

Responsibilities:

register agent
heartbeat
discover agent by capability
list agents

Keep registry very small and stable.

⸻

5. Coordinator Service Structure

Coordinator is the workflow brain.

coordinator-service
│
├── src/main/java/com/company/coordinator
│
│   ├── controller
│   │     WorkflowController
│   │
│   ├── service
│   │     WorkflowOrchestrator
│   │
│   ├── client
│   │     AgentRegistryClient
│   │     AgentExecutionClient
│   │
│   ├── workflow
│   │     ProductAnalysisWorkflow
│   │     RiskAnalysisWorkflow
│   │
│   ├── model
│   │     WorkflowRequest
│   │     WorkflowResult
│   │
│   └── config
│         AgentClientConfig
│
└── CoordinatorApplication.java

Coordinator responsibilities:

receive user requests
plan agent workflow
discover agents
dispatch tasks
aggregate results

Coordinator should not implement business logic — agents do that.

⸻

6. Agent Service Structure

Each agent is its own Spring Boot service.

Example:

agents/pricing-agent

Structure:

pricing-agent
│
├── src/main/java/com/company/pricing
│
│   ├── controller
│   │     TaskController
│   │
│   ├── service
│   │     PricingService
│   │
│   ├── capability
│   │     PriceLookupCapability
│   │
│   ├── client
│   │     ExternalPricingAPI
│   │
│   ├── config
│   │     AgentConfig
│   │
│   └── bootstrap
│         AgentRegistration
│
└── PricingAgentApplication.java

Agents should expose a standard A2A endpoint:

POST /tasks


⸻

7. Shared Libraries

Shared libraries are critical to avoid protocol drift.

A2A Protocol Module

shared/a2a-protocol

Contains:

TaskRequest
TaskResponse
TaskStatus
AgentCapability
AgentMetadata

Example:

public class TaskRequest {

    private String taskId;
    private String capability;
    private Map<String, Object> input;

}


⸻

Agent SDK

shared/agent-sdk

Provides helpers for agents:

register agent
send heartbeat
discover agents
send tasks

Example usage:

agentClient.sendTask(agentEndpoint, taskRequest);


⸻

Common Models

shared/common-models

Contains shared domain objects.

Example:

Product
PriceInfo
ReviewSummary
RiskReport


⸻

8. Dependency Structure

Important rule:

agents → shared libs
coordinator → shared libs
registry → shared libs

But:

agents should NOT depend on coordinator

This prevents circular dependencies.

⸻

9. Build Strategy

Use Gradle multi-module or Maven multi-module.

Example Maven root:

<modules>
  <module>registry-service</module>
  <module>coordinator-service</module>
  <module>agents/pricing-agent</module>
  <module>agents/research-agent</module>
  <module>shared/a2a-protocol</module>
</modules>

Benefits:
	•	shared dependency versions
	•	unified CI
	•	easier builds

⸻

10. Kubernetes Deployment Structure

infra/helm
│
├── registry-chart
├── coordinator-chart
├── pricing-agent-chart
├── research-agent-chart
└── review-agent-chart

Each service runs independently in EKS.

Example deployment:

pricing-agent
replicas: 3

Coordinator:

replicas: 2

Registry:

replicas: 2


⸻

11. Configuration Strategy

Each service should have:

application.yml
application-prod.yml

Example:

agent:
  id: pricing-agent
  capabilities:
    - price_lookup
    - price_analysis


⸻

12. Observability Layer

Add shared logging and tracing.

Structure:

shared/observability

Provides:

OpenTelemetry config
logging config
metrics config


⸻

13. Recommended Package Naming

Use domain-based packages.

Example:

com.company.agent.pricing
com.company.agent.research
com.company.registry
com.company.coordinator

Avoid:

com.company.service1


⸻

14. Development Workflow

Developer workflow:

1 create new agent module
2 implement capability
3 register capability
4 deploy agent

Coordinator automatically discovers it.

This makes the system extensible.

⸻

15. What This Structure Enables

With this structure you can grow to:

20+ agents
multiple coordinators
multiple workflows

Without refactoring core architecture.

⸻

✅ Key principle

Treat agents like specialized microservices with reasoning capabilities.

The architecture should follow good microservice design, not experimental LLM code.

⸻

If you’d like, I can also show something extremely valuable for your next step:

“The cleanest way to implement A2A task routing in Spring Boot (without creating a fragile agent framework).”

This avoids a lot of mistakes teams make when building their own agent infrastructure.
