
When teams implement A2A in Spring Boot, the biggest mistake is accidentally building a large “agent framework” inside their codebase. That becomes fragile, hard to maintain, and difficult to evolve.

A cleaner approach is to treat A2A routing like a lightweight RPC layer with capability-based dispatch. Below is a simple, production-friendly pattern that works well with Spring Boot + Embabel + Mongo + Redis + EKS.

⸻

1. Core Idea: Capability-Based Task Routing

Instead of building complex agent logic, use a simple pattern:

Task → capability → handler

Example flow:

POST /tasks
   │
   ▼
Task Router
   │
   ▼
Capability Handler
   │
   ▼
Business Service

Each agent declares capabilities, and each capability maps to a handler.

⸻

2. Define a Simple A2A Task Model

Keep your protocol simple.

public class TaskRequest {

    private String taskId;
    private String capability;
    private Map<String, Object> input;

}

Response:

public class TaskResponse {

    private String taskId;
    private String status;
    private Object result;

}

Status values typically:

accepted
completed
failed


⸻

3. Standard Task Endpoint

Every agent exposes the same endpoint.

@RestController
@RequestMapping("/tasks")
public class TaskController {

    private final TaskRouter router;

    @PostMapping
    public TaskResponse handleTask(@RequestBody TaskRequest task) {
        return router.route(task);
    }

}

Now all A2A communication becomes:

POST /tasks

This keeps the protocol stable.

⸻

4. Capability Handler Interface

Instead of large switch statements, use a handler interface.

public interface CapabilityHandler {

    String capability();

    TaskResponse handle(TaskRequest request);

}

Each capability becomes a small class.

⸻

5. Example Capability Implementation

Example pricing capability:

@Component
public class PriceLookupHandler implements CapabilityHandler {

    private final PricingService pricingService;

    @Override
    public String capability() {
        return "price_lookup";
    }

    @Override
    public TaskResponse handle(TaskRequest request) {

        String productId =
            (String) request.getInput().get("productId");

        Price price =
            pricingService.lookup(productId);

        return new TaskResponse(
            request.getTaskId(),
            "completed",
            price
        );
    }

}

This keeps business logic separate.

⸻

6. Task Router Implementation

Spring automatically discovers all handlers.

@Component
public class TaskRouter {

    private final Map<String, CapabilityHandler> handlers;

    public TaskRouter(List<CapabilityHandler> handlerList) {

        this.handlers =
            handlerList.stream()
                .collect(Collectors.toMap(
                    CapabilityHandler::capability,
                    h -> h
                ));
    }

    public TaskResponse route(TaskRequest request) {

        CapabilityHandler handler =
            handlers.get(request.getCapability());

        if (handler == null) {
            throw new RuntimeException(
                "Unknown capability: "
                + request.getCapability());
        }

        return handler.handle(request);
    }

}

Advantages:
	•	no large condition blocks
	•	extensible
	•	Spring manages handlers

⸻

7. Agent Capability Registration

Agents register capabilities in the registry at startup.

Example config:

agent:
  id: pricing-agent
  capabilities:
    - price_lookup
    - price_analysis

Startup registration:

@PostConstruct
public void register() {

    registryClient.register(
        agentId,
        endpoint,
        capabilities
    );

}


⸻

8. Coordinator Routing Logic

Coordinator asks registry for agents with capability.

Example:

List<AgentInfo> agents =
    registryClient.findByCapability("price_lookup");

Select agent:

AgentInfo agent = agents.get(0);

Send task:

restTemplate.postForObject(
    agent.getEndpoint() + "/tasks",
    taskRequest,
    TaskResponse.class
);


⸻

9. Retry and Timeout Strategy

Add simple resilience.

Example using Spring Retry:

@Retryable(
    value = Exception.class,
    maxAttempts = 3
)
public TaskResponse sendTask(...) {

Add timeouts via WebClient or RestTemplate config.

⸻

10. Async Task Support (Optional but Recommended)

Some tasks are slow.

Support async tasks:

POST /tasks

Returns:

taskId
status = accepted

Client polls:

GET /tasks/{taskId}

Store task state in Redis.

⸻

11. Observability

Add tracing around task routing.

Example:

traceId
taskId
capability
agentId
latency

Use:
	•	OpenTelemetry
	•	Prometheus
	•	Grafana

This makes debugging agent workflows possible.

⸻

12. Why This Pattern Works

This approach avoids building a fragile framework because:

Bad Approach	Clean Approach
Huge orchestration engine	simple router
reflection-heavy magic	explicit handlers
tight coupling	capability-based
complex runtime	Spring-managed beans

Your system remains simple and maintainable.

⸻

13. How This Scales to Many Agents

As you add agents:

pricing-agent
review-agent
research-agent
risk-agent
inventory-agent

Each agent simply adds handlers:

CapabilityHandler implementations

No architecture changes required.

⸻

14. Example Real Request Flow

User request
   │
   ▼
Coordinator
   │
   ▼
Registry lookup
   │
   ▼
Agent /tasks endpoint
   │
   ▼
TaskRouter
   │
   ▼
CapabilityHandler
   │
   ▼
Business logic


⸻

15. Golden Rule

Keep the A2A layer extremely thin.

It should only do:

task routing
capability dispatch
error handling

All real logic belongs in services, not the routing layer.

⸻

✅ If you’d like, I can also show something that becomes critical once your platform grows:

“How to prevent agent call loops and runaway workflows in A2A systems.”

This is one of the biggest production problems in multi-agent architectures.
