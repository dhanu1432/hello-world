# Enterprise Architecture Rules — Spring Boot Microservice

> **Target Stack:** Java 21 · Spring Boot 3.x (4.x ready) · MongoDB · AWS EKS · REST · Embabel Agent Framework  
> **Architecture Style:** Clean Architecture (Hexagonal / Ports & Adapters)  
> **Application:** Multi-Agent Troubleshooting Chatbot (Wireless & Broadband)

---

## 1. Clean Architecture — Package Structure & Dependency Rules

### 1.1 Canonical Package Layout

```
com.company.servicename
├── core/                          # ← Pure Java. ZERO framework imports.
│   ├── domain/                    #    Entities, Value Objects, Enums
│   │   ├── ChatSession.java
│   │   ├── TroubleshootingIntent.java   (sealed interface)
│   │   └── AgentResponse.java          (record)
│   ├── port/                      #    Interfaces (Ports)
│   │   ├── inbound/               #      Driving Ports (use-case boundaries)
│   │   │   ├── StartChatUseCase.java
│   │   │   └── SendMessageUseCase.java
│   │   └── outbound/              #      Driven Ports (infrastructure contracts)
│   │       ├── ChatSessionRepository.java
│   │       ├── WirelessAgentPort.java
│   │       └── BroadbandAgentPort.java
│   └── usecase/                   #    Use-Case Implementations (Orchestration Logic)
│       ├── OrchestratorService.java
│       └── IntentClassifier.java
│
├── infrastructure/                # ← Framework-aware. Implements Ports.
│   ├── web/                       #    REST Controllers (Driving Adapters)
│   │   ├── ChatController.java
│   │   └── dto/
│   │       ├── ChatRequest.java   (record)
│   │       └── ChatResponse.java  (record)
│   ├── persistence/               #    MongoDB (Driven Adapter)
│   │   ├── MongoChatSessionAdapter.java
│   │   ├── MongoChatSessionRepository.java  (Spring Data interface)
│   │   └── document/
│   │       └── ChatSessionDocument.java
│   ├── agent/                     #    Embabel / LLM (Driven Adapter)
│   │   ├── EmbabelWirelessAgent.java
│   │   └── EmbabelBroadbandAgent.java
│   └── config/                    #    Spring @Configuration beans
│       ├── MongoConfig.java
│       ├── ResilienceConfig.java
│       └── WebConfig.java
│
└── Application.java               # @SpringBootApplication entry point
```

### 1.2 The Dependency Rule (STRICTLY ENFORCED)

| Layer | Can Depend On | MUST NOT Depend On |
|---|---|---|
| `core.domain` | Nothing (pure Java only) | Spring, MongoDB, Embabel, Jackson |
| `core.port` | `core.domain` | Spring, MongoDB, Embabel |
| `core.usecase` | `core.domain`, `core.port` | Spring, MongoDB, Embabel |
| `infrastructure.*` | `core.*`, Spring, MongoDB, Embabel | — |

> [!CAUTION]
> **The `core` package must NEVER import any class from `org.springframework.*`, `org.mongodb.*`, or any Embabel package.** Violations must be caught by ArchUnit tests in CI (see Section 9).

### 1.3 Mapping Between Layers

- Domain entities (`core.domain`) are **not** the same as persistence documents (`infrastructure.persistence.document`).
- A dedicated **Mapper** class must exist to convert between Domain ↔ Document and Domain ↔ DTO.
- Use MapStruct or hand-written mappers. Never expose persistence annotations (`@Document`, `@Id`) to the `core` package.

---

## 2. Java 21 Coding Standards

### 2.1 Records for Immutable Data

- **All DTOs** (request/response), **event payloads**, and **value objects** must be Java `record` classes.
- Records are immutable by default, which prevents concurrency bugs in a virtual-thread environment.

```java
// ✅ Correct
public record ChatRequest(String sessionId, String userMessage) {}

// ❌ Forbidden — Mutable POJO as DTO
public class ChatRequest {
    private String sessionId; // mutable, thread-unsafe
    ...
}
```

### 2.2 Sealed Interfaces for Finite Domain Types

- When the domain has a **fixed, known set of variants** (e.g., intent types, agent types), use `sealed interface` + `record` implementations + exhaustive `switch`.

```java
public sealed interface TroubleshootingIntent
    permits WirelessIntent, BroadbandIntent, UnknownIntent {

    record WirelessIntent(String issueCategory) implements TroubleshootingIntent {}
    record BroadbandIntent(String issueCategory) implements TroubleshootingIntent {}
    record UnknownIntent(String rawInput) implements TroubleshootingIntent {}
}
```

```java
// Exhaustive switch — compiler error if a new intent is added but not handled
return switch (intent) {
    case WirelessIntent w  -> wirelessAgentPort.handle(w);
    case BroadbandIntent b -> broadbandAgentPort.handle(b);
    case UnknownIntent u   -> fallbackResponse(u);
};
```

### 2.3 Virtual Threads (MANDATORY)

- **Enable in `application.yml`:**
  ```yaml
  spring:
    threads:
      virtual:
        enabled: true
  ```
- This replaces platform threads with lightweight virtual threads for all request-handling and scheduled tasks. Critical for I/O-heavy agent/LLM calls.
- **Rule:** Never use `synchronized` blocks or `ReentrantLock` in request-handling code paths. These pin virtual threads to platform threads and destroy throughput. Use `java.util.concurrent` constructs instead.

### 2.4 Null Safety

- **Rule:** No method in the `core` package may return `null`.
- Use `Optional<T>` for values that may be absent (e.g., `Optional<ChatSession> findById(String id)`).
- Mark all Spring-facing parameters with `@NonNull` / `@Nullable` (from `org.springframework.lang`).

---

## 3. MongoDB & Data Layer Rules

### 3.1 Document Design — Aggregate Root Pattern

- Each MongoDB collection corresponds to **one Aggregate Root**.
- A `ChatSession` document should embed all its child data (messages, agent responses, metadata) in a single document. Do **not** normalize like a relational database.

```java
@Document(collection = "chat_sessions")
public class ChatSessionDocument {
    @Id
    private String id;
    @Version
    private Long version;            // Optimistic locking

    private String userId;
    private Instant createdAt;
    private Instant updatedAt;
    private List<MessageSubdocument> messages;  // Embedded, not a separate collection
    private String currentAgentType;
}
```

### 3.2 Optimistic Locking (MANDATORY)

- All mutable aggregate root documents **must** use `@Version`.
- When two concurrent requests try to update the same `ChatSession`, Spring Data will throw `OptimisticLockingFailureException`. The application must catch and retry gracefully.

### 3.3 Indexing Strategy

- **Rule:** Every query executed by the application must be backed by a MongoDB index. No full collection scans in production.
- Define indexes via `@CompoundIndex` annotations or a migration script (Mongock).
- Required indexes at minimum: `userId`, `createdAt`, `status`.

### 3.4 Schema Migration

- Use **Mongock** (or Liquibase for MongoDB) for all schema migrations (new indexes, data transformations).
- Migrations must be versioned, idempotent, and run at application startup.

### 3.5 No Direct Repository Access from Controllers

- Controllers must **never** inject or call a Repository directly.
- Data flow: `Controller → UseCase (via Port) → Repository (via Port)`.

---

## 4. REST API Rules

### 4.1 API Versioning

- All endpoints must be versioned in the URI path: `/api/v1/chat/sessions`.
- When a breaking change is needed, introduce `/api/v2/...` and maintain backward compatibility for at least one release cycle.

### 4.2 Standardized Error Responses — RFC 7807

- Implement a global `@RestControllerAdvice` that returns **RFC 7807 Problem Details** for all errors.
- Every error response must include: `type`, `title`, `status`, `detail`, and `instance`.

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ChatSessionNotFoundException.class)
    public ProblemDetail handleNotFound(ChatSessionNotFoundException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
            HttpStatus.NOT_FOUND, ex.getMessage());
        pd.setTitle("Chat Session Not Found");
        pd.setType(URI.create("https://docs.company.com/errors/session-not-found"));
        return pd;
    }
}
```

### 4.3 Request Validation

- All incoming `@RequestBody` DTOs must be validated with Jakarta Bean Validation (`@NotBlank`, `@Size`, `@Valid`).
- Validation failures must be caught by the `@RestControllerAdvice` and returned as a `400 Bad Request` with field-level error details.

### 4.4 HTTP Client

- **Use `RestClient`** (introduced in Spring 3.2) for all outgoing HTTP calls.
- `RestTemplate` is legacy and must not be used in new code.
- `WebClient` (reactive) should only be used if you explicitly need non-blocking reactive streams.

### 4.5 API Documentation

- All REST endpoints must be documented using **SpringDoc OpenAPI** (Swagger UI auto-generated).
- Every endpoint, parameter, and response schema must have a description annotation.

---

## 5. Resilience & Fault Tolerance Rules

### 5.1 Resilience4j (MANDATORY for all external calls)

Every call that leaves the JVM (MongoDB, LLM/Embabel agents, external HTTP APIs) must be wrapped with Resilience4j:

| Pattern | When to Use | Configuration |
|---|---|---|
| **Circuit Breaker** | LLM / Agent calls | `failureRateThreshold=50`, `waitDurationInOpenState=30s` |
| **Retry** | MongoDB transient failures | `maxAttempts=3`, `waitDuration=500ms`, exponential backoff |
| **Timeout** | All external calls | LLM calls: `30s`, MongoDB: `5s`, HTTP APIs: `10s` |
| **Bulkhead** | Limit concurrent LLM calls | `maxConcurrentCalls=20` (prevents overwhelming LLM provider) |

### 5.2 Graceful Degradation

- If the Wireless or Broadband agent is unavailable (circuit open), the Orchestrator **must not throw a 500**. It must return a graceful fallback message: *"I'm experiencing difficulties with my diagnostic tools. Let me transfer you to a human agent."*

### 5.3 Idempotency

- All state-changing operations must include an **idempotency key** (passed as an HTTP header: `X-Idempotency-Key`).
- The server must detect duplicate requests and return the cached response instead of processing again.

---

## 6. Observability Rules

### 6.1 Structured Logging

- **Format:** All logs must be emitted as structured JSON (use Logback + `logstash-logback-encoder`).
- **Correlation ID:** Every log line must include a `traceId` for distributed tracing. Use Micrometer Tracing (formerly Spring Cloud Sleuth) to auto-propagate trace IDs.
- **Sensitive Data:** Never log PII (customer phone numbers, account details). Mask or redact.

```json
{
  "timestamp": "2026-03-06T21:00:00Z",
  "level": "INFO",
  "traceId": "abc123def456",
  "logger": "OrchestratorService",
  "message": "Routed to WirelessAgent",
  "sessionId": "sess-789",
  "agentType": "WIRELESS"
}
```

### 6.2 Metrics (Prometheus + Micrometer)

- Spring Boot Actuator must expose a `/actuator/prometheus` endpoint.
- **Custom business metrics are mandatory:**
  - `chat.sessions.active` (Gauge)
  - `chat.messages.total` (Counter, tagged by `agent_type`)
  - `agent.response.latency` (Timer, tagged by `agent_type`)
  - `agent.circuit.breaker.state` (Gauge)

### 6.3 Health Probes for EKS

```yaml
# application.yml
management:
  endpoint:
    health:
      probes:
        enabled: true
      group:
        liveness:
          include: livenessState
        readiness:
          include: readinessState, mongo
  health:
    mongo:
      enabled: true
```

| Probe | Checks | Kubernetes Use |
|---|---|---|
| `/actuator/health/liveness` | JVM alive | Restart pod if fails |
| `/actuator/health/readiness` | JVM + MongoDB reachable | Stop routing traffic if fails |

---

## 7. Security Rules

### 7.1 Authentication & Authorization

- All endpoints (except `/actuator/health/**`) must require authentication.
- Use **OAuth 2.0 / JWT Bearer Tokens** validated via Spring Security's Resource Server.
- Role-based access control (RBAC) must be enforced at the method level using `@PreAuthorize`.

### 7.2 Secrets Management

- **NEVER** store secrets (API keys, DB credentials, LLM tokens) in `application.yml`, environment variables baked into Docker images, or source code.
- Use **AWS Secrets Manager** or **Kubernetes Secrets** (mounted as volumes, not env vars) and integrate via Spring Cloud AWS.

### 7.3 Input Sanitization

- All user input (chat messages) must be sanitized before being passed to LLM prompts to prevent **Prompt Injection** attacks.
- Implement a dedicated `InputSanitizer` component in the `core.usecase` layer.

### 7.4 Rate Limiting

- Enforce rate limits per user/session to prevent abuse (e.g., max 60 messages per minute per session).
- Use Spring Cloud Gateway or a custom `Filter` with a token-bucket algorithm backed by Redis or in-memory.

---

## 8. Agent-Specific Architecture Rules (Embabel)

### 8.1 Prompt Externalization

- **All LLM prompts must be stored in `src/main/resources/prompts/`** as `.txt` or `.st` (StringTemplate) files.
- Prompts must **never** be hardcoded as Java string literals in service classes.
- This allows prompt tuning without recompilation.

```
src/main/resources/prompts/
├── orchestrator/
│   ├── intent-classification.txt
│   └── fallback-response.txt
├── wireless-agent/
│   ├── system-prompt.txt
│   └── troubleshooting-flow.txt
└── broadband-agent/
    ├── system-prompt.txt
    └── diagnostic-steps.txt
```

### 8.2 Agent Isolation

- Each specialized agent (Wireless, Broadband) must be behind its own **Port interface** in the `core` layer.
- The Orchestrator must never directly instantiate or know the concrete Embabel class. It only interacts via the Port.

### 8.3 Conversation Context Management

- Chat history passed to agents must be **bounded**. Define a maximum context window (e.g., last 20 messages) to prevent token limit overflows and cost spikes.
- Implement a `ContextWindowStrategy` interface in the `core` layer with implementations like `SlidingWindowStrategy` or `SummarizationStrategy`.

### 8.4 Agent Response Validation

- Every response from an agent must be validated before being sent to the user.
- Implement a `ResponseValidator` component that checks for:
  - Empty or null responses
  - Responses containing PII or internal system details
  - Hallucinated links or phone numbers

---

## 9. Testing Rules

### 9.1 Testing Pyramid

| Level | What to Test | Tools | Coverage Target |
|---|---|---|---|
| **Unit Tests** | `core.*` (domain, use cases, orchestrator logic) | JUnit 5 + Mockito | ≥ 80% line coverage |
| **Integration Tests** | `infrastructure.*` (Mongo, REST, Embabel adapters) | Testcontainers (MongoDB), MockWebServer | Key paths covered |
| **Architecture Tests** | Dependency rule enforcement | **ArchUnit** | 100% of rules |
| **Contract Tests** | API schema compatibility | Spring Cloud Contract or Pact | All public endpoints |

### 9.2 ArchUnit — Dependency Rule Enforcement (MANDATORY)

```java
@AnalyzeClasses(packages = "com.company.servicename")
class ArchitectureRulesTest {

    @ArchTest
    static final ArchRule core_must_not_depend_on_infrastructure =
        noClasses()
            .that().resideInAPackage("..core..")
            .should().dependOnClassesThat()
            .resideInAPackage("..infrastructure..");

    @ArchTest
    static final ArchRule core_must_not_use_spring =
        noClasses()
            .that().resideInAPackage("..core..")
            .should().dependOnClassesThat()
            .resideInAPackage("org.springframework..");

    @ArchTest
    static final ArchRule controllers_must_not_access_repositories =
        noClasses()
            .that().resideInAPackage("..web..")
            .should().dependOnClassesThat()
            .resideInAPackage("..persistence..");
}
```

### 9.3 Testcontainers for MongoDB

- Integration tests must use **Testcontainers** to spin up a real MongoDB instance. Never mock the database for integration-level tests.
- Use `@ServiceConnection` (Spring Boot 3.1+) for auto-configuration.

---

## 10. Configuration Management

### 10.1 Profile Strategy

| Profile | Purpose | Activated By |
|---|---|---|
| `default` | Local development | `./mvnw spring-boot:run` |
| `test` | CI/CD test pipeline | `@ActiveProfiles("test")` |
| `staging` | Pre-production on EKS | `SPRING_PROFILES_ACTIVE=staging` |
| `prod` | Production on EKS | `SPRING_PROFILES_ACTIVE=prod` |

### 10.2 Configuration Hierarchy

```
application.yml           ← Shared defaults (server port, actuator config)
application-staging.yml   ← Staging overrides (staging MongoDB URI)
application-prod.yml      ← Production overrides (prod MongoDB URI)
```

- Sensitive values (URIs, API keys) must **not** exist in any `.yml` file. They must be injected via Kubernetes Secrets or AWS Secrets Manager at runtime.

---

## 11. EKS Deployment Rules

### 11.1 Dockerfile Best Practices

```dockerfile
FROM eclipse-temurin:21-jre-alpine AS runtime
WORKDIR /app
COPY target/*.jar app.jar

ENTRYPOINT ["java", \
  "-XX:MaxRAMPercentage=75.0", \
  "-XX:+UseZGC", \
  "-jar", "app.jar"]
```

| Flag | Purpose |
|---|---|
| `MaxRAMPercentage=75.0` | JVM respects EKS pod memory limits, prevents OOMKill |
| `+UseZGC` | Low-latency garbage collector, ideal for chatbot apps requiring consistent response times |

### 11.2 Graceful Shutdown

```yaml
# application.yml
server:
  shutdown: graceful

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

- When EKS sends a SIGTERM (during scaling or rolling update), Spring will stop accepting new requests but allow active agent calls up to 30 seconds to complete.

### 11.3 Resource Requests & Limits

- Every Kubernetes Deployment manifest must specify CPU and memory `requests` and `limits`.
- Start with: `requests: 512Mi / 500m CPU`, `limits: 1Gi / 1000m CPU`. Tune based on load testing.

---

## 12. CI/CD Pipeline Gates

Every PR and merge to `main` must pass these gates **in order**:

```
1. ✅ Compile           → mvn compile
2. ✅ Unit Tests        → mvn test (includes ArchUnit)
3. ✅ Integration Tests → mvn verify -P integration (Testcontainers)
4. ✅ Static Analysis   → SonarQube / SpotBugs / PMD
5. ✅ Container Build   → docker build
6. ✅ Container Scan    → Trivy / Snyk (CVE scan the Docker image)
7. ✅ Deploy to Staging → Helm upgrade to EKS staging namespace
8. ✅ Smoke Tests       → Automated health check + one happy-path chat flow
9. ✅ Deploy to Prod    → Manual approval gate → Helm upgrade to EKS prod namespace
```

> [!IMPORTANT]
> **No code reaches production without passing ALL 8 automated gates.** The production deploy (gate 9) requires manual approval from a tech lead or architect.

---

## 13. Spring Boot 4.x Readiness Checklist

Since you plan to upgrade to Spring Boot 4.x, follow these rules now to minimize migration pain:

- [x] Use Jakarta EE (`jakarta.*`) namespace, not `javax.*` (already enforced in Spring Boot 3.x).
- [ ] Avoid deprecated Spring APIs. Run `mvn compile` with `-Xlint:deprecation` and fix all warnings.
- [ ] Do not rely on `spring.factories` for auto-configuration. Use `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` instead (Spring Boot 3.x forward-compatible mechanism).
- [ ] Track the [Spring Boot 4.x milestone](https://github.com/spring-projects/spring-boot/milestone/) for breaking changes.

---

## Quick Reference Card

| Concern | Rule | Enforcement |
|---|---|---|
| **Architecture** | Clean Architecture, Dependency Rule | ArchUnit in CI |
| **Data Types** | Records for DTOs/VOs, Sealed for variants | Code Review |
| **Threads** | Virtual Threads ON, no `synchronized` | Config + SpotBugs |
| **MongoDB** | Aggregate Root, `@Version`, indexed queries | Code Review + Mongock |
| **REST** | Versioned URIs, RFC 7807 errors, `RestClient` | Code Review + Contract Tests |
| **Resilience** | Circuit Breaker + Retry + Timeout on all external calls | Resilience4j config |
| **Logging** | Structured JSON, traceId, no PII | Logback config + Code Review |
| **Security** | OAuth 2.0 JWT, Secrets Manager, Prompt Sanitization | Spring Security + Code Review |
| **Prompts** | Externalized in `/resources/prompts/` | Code Review |
| **Testing** | Unit ≥ 80%, ArchUnit, Testcontainers | CI gates |
| **Deployment** | `MaxRAMPercentage=75`, ZGC, Graceful Shutdown | Dockerfile + Helm |
