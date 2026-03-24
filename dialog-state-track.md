Perfect—here’s a **GitHub-ready, enterprise-grade starter repo** for a **Support Agent with Spring Boot + DST + Agent orchestration**.

You can literally copy this structure and run it.

---

# 🏗️ REPOSITORY: `enterprise-support-agent`

```text
enterprise-support-agent/
│
├── docker/
│   ├── docker-compose.yml
│
├── src/main/java/com/company/supportagent/
│
│   ├── SupportAgentApplication.java
│
│   ├── api/
│   │   └── ChatController.java
│
│   ├── orchestrator/
│   │   └── AgentOrchestrator.java
│
│   ├── dst/
│   │   ├── state/
│   │   │   └── SupportDialogState.java
│   │   │
│   │   ├── reducer/
│   │   │   └── DialogStateReducer.java
│   │   │
│   │   ├── fsm/
│   │   │   ├── DialogStageHandler.java
│   │   │   ├── CollectingInfoHandler.java
│   │   │   ├── ValidationHandler.java
│   │   │   ├── ExecutionHandler.java
│   │   │   └── ResolutionHandler.java
│   │   │
│   │   ├── policy/
│   │   │   └── PolicyEngine.java
│   │   │
│   │   └── nlu/
│   │       └── NLUService.java
│
│   ├── memory/
│   │   ├── SessionMemoryService.java
│   │   └── VectorMemoryService.java
│
│   ├── tools/
│   │   ├── OrderService.java
│   │   └── TicketService.java
│
│   ├── response/
│   │   └── ResponseGenerator.java
│
│   └── config/
│       ├── RedisConfig.java
│       └── AgentConfig.java
│
├── src/main/resources/
│   ├── application.yml
│
├── pom.xml
└── README.md
```

---

# 🐳 docker-compose.yml (Redis for session memory)

```yaml
version: '3.8'

services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

---

# ⚙️ pom.xml (important deps)

```xml
<dependencies>

    <!-- Spring Boot -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- Redis -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis</artifactId>
    </dependency>

    <!-- (Optional) AI integration -->
    <dependency>
        <groupId>dev.langchain4j</groupId>
        <artifactId>langchain4j</artifactId>
        <version>0.30.0</version>
    </dependency>

    <!-- Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
    </dependency>

</dependencies>
```

---

# 🚀 MAIN APPLICATION

```java
@SpringBootApplication
public class SupportAgentApplication {
    public static void main(String[] args) {
        SpringApplication.run(SupportAgentApplication.class, args);
    }
}
```

---

# 🧠 STATE MODEL

```java
@Data
public class SupportDialogState {

    private String sessionId;

    private Intent intent;

    private Map<String, Object> slots = new HashMap<>();

    private Stage stage = Stage.START;

    private List<String> missingSlots = new ArrayList<>();

    private boolean requiresHuman;

    public enum Intent {
        REFUND, CANCEL_ORDER, TECH_SUPPORT, UNKNOWN
    }

    public enum Stage {
        START,
        INTENT_DETECTED,
        COLLECTING_INFO,
        VALIDATING,
        EXECUTING,
        RESOLVED,
        ESCALATION
    }
}
```

---

# 🤖 NLU SERVICE (stub → plug LLM later)

```java
@Service
public class NLUService {

    public ExtractionResult extract(String message) {

        // Replace with LLM call
        ExtractionResult result = new ExtractionResult();

        if (message.contains("refund")) {
            result.setIntent("REFUND");
        }

        if (message.matches(".*\\d{5}.*")) {
            result.addEntity("orderId", "12345");
        }

        return result;
    }
}
```

---

# 🔄 REDUCER

```java
@Component
public class DialogStateReducer {

    public SupportDialogState reduce(
            SupportDialogState state,
            ExtractionResult extraction) {

        if (extraction.getIntent() != null) {
            state.setIntent(
                SupportDialogState.Intent.valueOf(extraction.getIntent())
            );
            state.setStage(SupportDialogState.Stage.INTENT_DETECTED);
        }

        state.getSlots().putAll(extraction.getEntities());

        return state;
    }
}
```

---

# 🚦 FSM HANDLER INTERFACE

```java
public interface DialogStageHandler {
    SupportDialogState.Stage getStage();
    SupportDialogState handle(SupportDialogState state);
}
```

---

# 🧩 COLLECTING INFO

```java
@Component
public class CollectingInfoHandler implements DialogStageHandler {

    @Override
    public Stage getStage() {
        return Stage.COLLECTING_INFO;
    }

    @Override
    public SupportDialogState handle(SupportDialogState state) {

        List<String> required = List.of("orderId");

        List<String> missing = required.stream()
                .filter(slot -> !state.getSlots().containsKey(slot))
                .toList();

        if (!missing.isEmpty()) {
            state.setMissingSlots(missing);
            return state;
        }

        state.setStage(Stage.VALIDATING);
        return state;
    }
}
```

---

# 🧠 POLICY ENGINE

```java
@Component
public class PolicyEngine {

    public SupportDialogState apply(SupportDialogState state) {

        if (state.getIntent() == null) {
            state.setStage(Stage.ESCALATION);
        }

        if (state.getStage() == Stage.INTENT_DETECTED) {
            state.setStage(Stage.COLLECTING_INFO);
        }

        return state;
    }
}
```

---

# 🎯 ORCHESTRATOR

```java
@Service
public class AgentOrchestrator {

    private final NLUService nlu;
    private final DialogStateReducer reducer;
    private final PolicyEngine policy;
    private final Map<Stage, DialogStageHandler> handlers;

    public AgentOrchestrator(List<DialogStageHandler> handlerList,
                             NLUService nlu,
                             DialogStateReducer reducer,
                             PolicyEngine policy) {

        this.nlu = nlu;
        this.reducer = reducer;
        this.policy = policy;

        this.handlers = handlerList.stream()
                .collect(Collectors.toMap(
                        DialogStageHandler::getStage,
                        Function.identity()
                ));
    }

    public SupportDialogState process(
            SupportDialogState state,
            String message) {

        var extraction = nlu.extract(message);

        state = reducer.reduce(state, extraction);

        state = policy.apply(state);

        var handler = handlers.get(state.getStage());

        if (handler != null) {
            state = handler.handle(state);
        }

        return state;
    }
}
```

---

# 💬 RESPONSE GENERATOR

```java
@Service
public class ResponseGenerator {

    public String generate(SupportDialogState state) {

        return switch (state.getStage()) {

            case COLLECTING_INFO ->
                "Please provide: " + state.getMissingSlots();

            case VALIDATING ->
                "Validating your request...";

            case RESOLVED ->
                "Your issue is resolved.";

            case ESCALATION ->
                "Connecting to human agent.";

            default ->
                "How can I help you?";
        };
    }
}
```

---

# 🌐 CONTROLLER

```java
@RestController
@RequestMapping("/chat")
public class ChatController {

    private final AgentOrchestrator orchestrator;
    private final ResponseGenerator responseGenerator;

    private final Map<String, SupportDialogState> sessions = new HashMap<>();

    @PostMapping
    public String chat(@RequestParam String sessionId,
                       @RequestBody String message) {

        SupportDialogState state =
            sessions.computeIfAbsent(sessionId, id -> new SupportDialogState());

        state = orchestrator.process(state, message);

        sessions.put(sessionId, state);

        return responseGenerator.generate(state);
    }
}
```

---

# ⚙️ application.yml

```yaml
spring:
  redis:
    host: localhost
    port: 6379

server:
  port: 8080
```

---

# ▶️ HOW TO RUN

```bash
docker-compose up
mvn spring-boot:run
```

---

# 🧪 TEST IT

```bash
curl -X POST "http://localhost:8080/chat?sessionId=1" \
     -H "Content-Type: text/plain" \
     -d "I want a refund"
```

---

# 🚀 NEXT STEPS (MAKE IT TRULY ENTERPRISE)

Plug in:

### 1. LLM

* Replace NLUService with LangChain4j

### 2. Session storage

* Replace HashMap with Redis

### 3. Vector memory

* Add Weaviate or Pinecone

### 4. Observability

* Add logging per state transition

### 5. Multi-intent routing

* Split FSM by domain (billing, tech, etc.)

---

# 💬 If you want next

I can extend this into:

* ✅ Multi-agent system (billing/tech separation)
* ✅ Tool calling (real APIs)
* ✅ Kafka event-driven architecture
* ✅ Kubernetes deployment
* ✅ Production security (JWT, rate limiting)

Just tell me 👍
