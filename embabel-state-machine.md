I have created a Flux Sink for streaming from my embabel agent app. as the app writes SSE events and messages, they will get transferred to client app and displayed. But embabel offers OuputChannel in...
Show full text
Fast
View as codemap
The OutputChannel interface in Embabel serves as an internal abstraction for routing agent output to various destinations, while your Flux Sink handles the specific use case of streaming to web clients via SSE. They serve complementary rather than replacement purposes.

Purpose of OutputChannel
OutputChannel is Embabel's unified mechanism for agents to send output to different destinations regardless of the user interface or integration point OutputChannel.kt:23-34 . It supports multiple event types:

MessageOutputChannelEvent: Chat messages (most common) OutputChannel.kt:52-55
ProgressOutputChannelEvent: Status updates and progress indicators OutputChannel.kt:85-88
LoggingOutputChannelEvent: Debug and informational messages OutputChannel.kt:73-78
ContentOutputChannelEvent: Rich content and assets OutputChannel.kt:57-60
How OutputChannel Works in Embabel
Agents interact with OutputChannel through several key integration points:

ProcessContext: Every agent process has access to an OutputChannel that combines platform and process-specific channels ProcessContext.kt:28-35

ChatSession: Uses OutputChannel to send messages via the saveAndSend() method ChatSession.kt:71-79

ActionContext: Provides convenience methods like sendMessage() and updateProgress() that use the underlying OutputChannel ActionContext.kt:47-51

Relationship with Your Flux Sink
Your Flux Sink and Embabel's OutputChannel can work together in two main approaches:

Approach 1: Bridge OutputChannel to Your Flux Sink
Create a custom OutputChannel implementation that writes to your existing Flux Sink:

class FluxSinkOutputChannel(private val sink: FluxSink<YourEvent>) : OutputChannel {  
    override fun send(event: OutputChannelEvent) {  
        when (event) {  
            is MessageOutputChannelEvent ->   
                sink.next(YourEvent.fromMessage(event.message))  
            is ProgressOutputChannelEvent ->   
                sink.next(YourEvent.fromProgress(event.message))  
            // Handle other event types...  
        }  
    }  
}
Approach 2: Use Embabel's Built-in SSE Streaming
Embabel already provides SSE streaming through SSEController which streams AgentProcessEvent objects SseController.kt:47-50 . This controller:

Buffers events per process SseController.kt:61-62
Handles multiple concurrent connections SseController.kt:58-59
Provides catch-up functionality for new connections SseController.kt:132-139
Key Differences
Aspect	OutputChannel	Your Flux Sink
Scope	Internal Embabel abstraction for all agent output	Your specific SSE streaming implementation
Event Types	Structured events (messages, progress, logging, content)	Your custom event format
Integration	Used throughout Embabel framework	Your application-specific streaming
Flexibility	Multiple implementations (terminal, multicast, Discord, etc.)	Single-purpose SSE streaming
Recommendation
Rather than replacing your Flux Sink, consider creating a bridge between them. This allows you to:

Leverage Embabel's rich event types and structured output
Maintain your existing SSE infrastructure
Benefit from Embabel's built-in features like progress tracking and logging
The MulticastOutputChannel implementation shows how to send events to multiple destinations simultaneously OutputChannel.kt:93-109 , which could be useful for sending to both your Flux Sink and other outputs like logs.

Notes
The OutputChannelHighlightingEventListener demonstrates how to listen to agent events and forward them to an OutputChannel OutputChannelHighlightingEventListener.kt:33-45
TerminalOutputChannel shows a concrete implementation that formats events for CLI display TerminalServices.kt:239-284
Embabel's streaming capabilities for LLM responses use a different mechanism (StreamingEvent) that's separate from OutputChannel page.adoc:10-14
Wiki pages you might want to explore:

User Interfaces (embabel/embabel-agent)
------------------------------------------------------
Embabel's streaming capabilities for LLM responses use a different mechanism (StreamingEvent) that's separate from OutputChannel how do I stream LLM responses in embabel? do I still need to use Flux S...
Show full text
Fast
View as codemap
You don't need to bridge both OutputChannel and LLM streaming to your Flux Sink. Embabel's LLM streaming uses a separate StreamingEvent mechanism that you can use directly or bridge to your existing sink.

LLM Streaming in Embabel
Emabel provides three main streaming methods through StreamingChatClientOperations StreamingChatClientOperations.kt:88-115 :

Raw Text Streaming: generateStream() - Returns Flux<String> of raw LLM chunks
Object Streaming: createObjectStream() - Returns Flux<T> of parsed objects
Mixed Streaming: createObjectStreamWithThinking() - Returns Flux<StreamingEvent<T>> with both thinking and objects
Using LLM Streaming
Option 1: Direct Streaming to Your Flux Sink
// Get streaming operations from your context  
val streamingOps = StreamingChatClientOperations(llmOperations)  
  
// Stream objects with thinking  
val eventStream: Flux<StreamingEvent<YourType>> = streamingOps.createObjectStreamWithThinking(  
    messages = messages,  
    interaction = interaction,  
    outputClass = YourType::class.java,  
    agentProcess = agentProcess,  
    action = action  
)  
  
// Bridge to your existing Flux Sink  
eventStream.subscribe { event ->  
    when {  
        event.isThinking() -> sink.next(YourEvent.fromThinking(event.getThinking()))  
        event.isObject() -> sink.next(YourEvent.fromObject(event.getObject()))  
    }  
}
Option 2: Use StreamingPromptRunnerBuilder
val results = StreamingPromptRunnerBuilder(runner)  
    .withStreaming()  
    .withPrompt(prompt)  
    .createObjectStreamWithThinking(YourType::class.java)  
  
results  
    .doOnNext { event ->  
        if (event.isThinking()) {  
            // Handle thinking events  
        } else if (event.isObject()) {  
            // Handle object events  
        }  
    }  
    .subscribe()
How StreamingEvent Works
The StreamingJacksonOutputConverter processes LLM responses in JSONL format StreamingJacksonOutputConverter.kt:107-131 :

Thinking blocks: content → StreamingEvent.Thinking
JSON objects: {"field": "value"} → StreamingEvent.Object
The converter handles mixed content where LLMs can output both reasoning and structured data StreamingJacksonOutputConverter.kt:75-101 .

Integration Strategy
You have two approaches:

Single Sink: Bridge only LLM streaming events to your Flux Sink, ignore OutputChannel for streaming
Dual Sinks: Use OutputChannel for agent events (progress, messages) and separately bridge LLM streaming events
The documentation shows examples with reactive callbacks using doOnNext, doOnError, doOnComplete page.adoc:31-57 .

Notes
LLM streaming requires ChatClientLlmOperations - check supportsStreaming() first
The StreamingEvent mechanism is completely separate from OutputChannel - they serve different purposes
You can see real integration examples in the test files for both Ollama and OpenAI streaming LLMOllamaStreamingBuilderIT.java:165-219


----------------------------------------------------------------
I have created a Flux Sink for streaming from my embabel agent app. as the app writes SSE events and messages, they will get transferred to client app and displayed. But embabel offers OuputChannel in...
Show full text
Fast
The OutputChannel interface in Embabel serves as an internal abstraction for routing agent output to various destinations, while your Flux Sink handles the specific use case of streaming to web clients via SSE. They serve complementary rather than replacement purposes.

Purpose of OutputChannel
OutputChannel is Embabel's unified mechanism for agents to send output to different destinations regardless of the user interface or integration point OutputChannel.kt:23-34 . It supports multiple event types:

MessageOutputChannelEvent: Chat messages (most common) OutputChannel.kt:52-55
ProgressOutputChannelEvent: Status updates and progress indicators OutputChannel.kt:85-88
LoggingOutputChannelEvent: Debug and informational messages OutputChannel.kt:73-78
ContentOutputChannelEvent: Rich content and assets OutputChannel.kt:57-60
How OutputChannel Works in Embabel
Agents interact with OutputChannel through several key integration points:

ProcessContext: Every agent process has access to an OutputChannel that combines platform and process-specific channels ProcessContext.kt:28-35

ChatSession: Uses OutputChannel to send messages via the saveAndSend() method ChatSession.kt:71-79

ActionContext: Provides convenience methods like sendMessage() and updateProgress() that use the underlying OutputChannel ActionContext.kt:47-51

Relationship with Your Flux Sink
Your Flux Sink and Embabel's OutputChannel can work together in two main approaches:

Approach 1: Bridge OutputChannel to Your Flux Sink
Create a custom OutputChannel implementation that writes to your existing Flux Sink:

class FluxSinkOutputChannel(private val sink: FluxSink<YourEvent>) : OutputChannel {  
    override fun send(event: OutputChannelEvent) {  
        when (event) {  
            is MessageOutputChannelEvent ->   
                sink.next(YourEvent.fromMessage(event.message))  
            is ProgressOutputChannelEvent ->   
                sink.next(YourEvent.fromProgress(event.message))  
            // Handle other event types...  
        }  
    }  
}
Approach 2: Use Embabel's Built-in SSE Streaming
Embabel already provides SSE streaming through SSEController which streams AgentProcessEvent objects SseController.kt:47-50 . This controller:

Buffers events per process SseController.kt:61-62
Handles multiple concurrent connections SseController.kt:58-59
Provides catch-up functionality for new connections SseController.kt:132-139
Key Differences
Aspect  OutputChannel   Your Flux Sink
Scope   Internal Embabel abstraction for all agent output   Your specific SSE streaming implementation
Event Types Structured events (messages, progress, logging, content)    Your custom event format
Integration Used throughout Embabel framework   Your application-specific streaming
Flexibility Multiple implementations (terminal, multicast, Discord, etc.)   Single-purpose SSE streaming
Recommendation
Rather than replacing your Flux Sink, consider creating a bridge between them. This allows you to:

Leverage Embabel's rich event types and structured output
Maintain your existing SSE infrastructure
Benefit from Embabel's built-in features like progress tracking and logging
The MulticastOutputChannel implementation shows how to send events to multiple destinations simultaneously OutputChannel.kt:93-109 , which could be useful for sending to both your Flux Sink and other outputs like logs.

Notes
The OutputChannelHighlightingEventListener demonstrates how to listen to agent events and forward them to an OutputChannel OutputChannelHighlightingEventListener.kt:33-45
TerminalOutputChannel shows a concrete implementation that formats events for CLI display TerminalServices.kt:239-284
Embabel's streaming capabilities for LLM responses use a different mechanism (StreamingEvent) that's separate from OutputChannel page.adoc:10-14
Wiki pages you might want to explore:

User Interfaces (embabel/embabel-agent)



embabel/embabel-agent
embabel-agent-api/src/main/kotlin/com/embabel/agent/api/channel/OutputChannel.kt


import com.embabel.chat.Message
import org.slf4j.LoggerFactory
 
/**
 * Allows agents to interact with the outside world through multiple channels
 */
interface OutputChannel {
 
    fun send(event: OutputChannelEvent)
 
    operator fun plus(other: OutputChannel): OutputChannel =
        if (this == DevNullOutputChannel) other else if (other == DevNullOutputChannel) this else MulticastOutputChannel(
            listOf(this, other)
        )
}
 
object DevNullOutputChannel : OutputChannel {
 

 * Most likely an Assistant message, but could also be a User message in some cases.
 * @param processId Process that generated this message
 */
data class MessageOutputChannelEvent(
    override val processId: String,
    val message: Message,
) : OutputChannelEvent
 
data class ContentOutputChannelEvent(
    override val processId: String,
    val content: HasContent,
) : OutputChannelEvent
 
/**
 * Logging or progress event

 * Ephemeral message.
 * Not meant to be part of a conversation
 */
data class LoggingOutputChannelEvent @JvmOverloads constructor(
    override val processId: String,
    override val message: String,
    val level: Level = Level.INFO,
    val throwable: Throwable? = null,
) : InformativeOutputChannelEvent {
 
    enum class Level {
        TRACE, DEBUG, INFO, WARN, ERROR
    }
}
 
data class ProgressOutputChannelEvent(
    override val processId: String,
    override val message: String,
) : InformativeOutputChannelEvent
 
/**
 * Send to all channels
 */
class MulticastOutputChannel(
    private val outputChannels: List<OutputChannel>,
) : OutputChannel {
 
    private val logger = LoggerFactory.getLogger(javaClass)
 
    override fun send(event: OutputChannelEvent) {
        outputChannels.forEach {
            try {
                it.send(event)
            } catch (t: Throwable) {
                logger.warn("Exception in onPlatformEvent from $it", t)
            }
        }
    }
 
}

embabel/embabel-agent
embabel-agent-api/src/main/kotlin/com/embabel/agent/core/ProcessContext.kt


 * Process state and services. Created by the platform,
 * not user code.
 */
data class ProcessContext(
    val processOptions: ProcessOptions = ProcessOptions(),
    internal val platformServices: PlatformServices,
    val outputChannel: OutputChannel = platformServices.outputChannel + processOptions.outputChannel,
    val agentProcess: AgentProcess,
) : LlmOperations by platformServices.llmOperations, AgenticEventListener by MulticastAgenticEventListener(
    processOptions.listeners + platformServices.eventListener,
) {
 
    val blackboard: Blackboard
        get() = agentProcess


embabel/embabel-agent
embabel-agent-api/src/main/kotlin/com/embabel/chat/ChatSession.kt


     * and send it to the output channel.
     * Preserves all message properties including awaitable and assets.
     */
    fun saveAndSend(message: AssistantMessage) {
        conversation.addMessage(message)
        outputChannel.send(
            MessageOutputChannelEvent(
                processId = processId ?: "anonymous",
                message = message,
            )
        )
    }
}

embabel/embabel-agent
embabel-agent-api/src/main/kotlin/com/embabel/agent/api/common/ActionContext.kt


    /**
     * Convenience method to send a message to the output channel of the process.
     */
    fun sendMessage(message: Message) {
        processContext.outputChannel.send(
            MessageOutputChannelEvent(agentProcess.id, message)
        )
    }
 
    /**
     * Convenience method to send a message to the output channel of the process


embabel/embabel-agent
embabel-agent-api/src/main/kotlin/com/embabel/agent/web/sse/SseController.kt


 * [AgenticEventListener].
 * Each new listener will receive all events for that process to date.
 */
@RestController
class SSEController(
    private val sseProperties: SseProperties,
) : AgenticEventListener {
 
    private val logger = LoggerFactory.getLogger(SSEController::class.java)
 

        logger.info("SSEController initialized, ready to stream AgentProcessEvents...")
    }
 
    // Map from processId to a list of SseEmitters
    private val processEmitters = ConcurrentHashMap<String, MutableList<SseEmitter>>()
 
    // Buffer recent events per process
    private val eventBuffer = ConcurrentHashMap<String, MutableList<AgentProcessEvent>>()
 
    override fun onProcessEvent(event: AgentProcessEvent) {
        val processId = event.processId


            removeEmitter(processId, emitter)
        }
 
        try {
            // Send any earlier events from the buffer
            eventBuffer[processId]?.let { buffer ->
                for (event in buffer) {
                    logger.debug("Catchup: Sending buffered event for process {}: {}", processId, event)
                    emitter.send(SseEmitter.event().name(SSE_EVENT_NAME).data(event))
                }
            }
 
            emitter.send(
                SseEmitter.event()


embabel/embabel-agent
embabel-agent-api/src/main/kotlin/com/embabel/agent/api/event/progress/OutputChannelHighlightingEventListener.kt


    private val verbose: Boolean = true,
) : AgenticEventListener {
 
    override fun onProcessEvent(event: AgentProcessEvent) {
        when (event) {
            is ToolCallRequestEvent -> {
                var message = "🔧 ${event.tool}"
                if (verbose) {
                    message += " with input `${event.toolInput}`"
                }
                outputChannel.send(
                    ProgressOutputChannelEvent(
                        processId = event.processId,
                        message = message,
                    )
                )
            }
 
            is LlmRequestEvent<*> -> {


embabel/embabel-agent
embabel-agent-shell/src/main/kotlin/com/embabel/agent/shell/TerminalServices.kt


    fun outputChannel(agentPlatform: AgentPlatform): OutputChannel =
        TerminalOutputChannel(agentPlatform)
 
    private inner class TerminalOutputChannel(
        private val agentPlatform: AgentPlatform,
        private val colorPalette: ColorPalette = DefaultColorPalette(),
    ) : OutputChannel {
 
        override fun send(event: OutputChannelEvent) {
            when (event) {
                is MessageOutputChannelEvent -> {
                    val formattedResponse = WordUtils.wrap(
                        "${event.message.sender}: ${event.message.content.color(colorPalette.color2)}",
                        shellProperties.lineLength,
                    )
                    println(formattedResponse)
                    val agentProcess = agentPlatform.getAgentProcess(event.processId)
                        ?: throw IllegalStateException("Process not found: ${event.processId}")
 
                    (event.message as? AssistantMessage)?.awaitable?.let { awaitable ->
                        val awaitableResponse = handleAwaitable(awaitable)
                        if (awaitableResponse == null) {
                            TODO()
                        }
                        (awaitable as Awaitable<*, AwaitableResponse>).onResponse(
                            response = awaitableResponse,
                            agentProcess = agentProcess,
                        )
                        agentProcess.run()
                    }
                }
 
                is ContentOutputChannelEvent -> {
                    println("Content event: ${event.content}")
                }
 
                is ProgressOutputChannelEvent -> {
                    println("▶ ${event.message}")
                }
 
                is LoggingOutputChannelEvent -> {
                    println("🪵 ${event.message}")
                }
 
                else -> {
                    println(event.toString())
                }
            }
        }
    }
 
    /**


embabel/embabel-agent
embabel-agent-docs/src/main/asciidoc/reference/streaming/page.adoc


This feature is well aligned with Embabel focus on object-oriented programming model.
==== Concepts
- ``StreamingEvent`` - wraps Thinking or user Object
-  ```StreamingPromptRunnerBuilder``` - runner with streaming capabilities
- Spring Reactive Programming Support for Spring AI ChatClient as underlying infrastructure
- All reactive callbacks, such as _doOnNext_, _doOnComplete_, etc. are at developer's disposal
==== Example - Simple Thinking and Object Streaming with Callbacks
[source,java]

embabel/embabel-agent
Embabel's streaming capabilities for LLM responses use a different mechanism (StreamingEvent) that's separate from OutputChannel how do I stream LLM responses in embabel? do I still need to use Flux S...
Show full text
Fast
You don't need to bridge both OutputChannel and LLM streaming to your Flux Sink. Embabel's LLM streaming uses a separate StreamingEvent mechanism that you can use directly or bridge to your existing sink.

LLM Streaming in Embabel
Emabel provides three main streaming methods through StreamingChatClientOperations StreamingChatClientOperations.kt:88-115 :

Raw Text Streaming: generateStream() - Returns Flux<String> of raw LLM chunks
Object Streaming: createObjectStream() - Returns Flux<T> of parsed objects
Mixed Streaming: createObjectStreamWithThinking() - Returns Flux<StreamingEvent<T>> with both thinking and objects
Using LLM Streaming
Option 1: Direct Streaming to Your Flux Sink
// Get streaming operations from your context  
val streamingOps = StreamingChatClientOperations(llmOperations)  
  
// Stream objects with thinking  
val eventStream: Flux<StreamingEvent<YourType>> = streamingOps.createObjectStreamWithThinking(  
    messages = messages,  
    interaction = interaction,  
    outputClass = YourType::class.java,  
    agentProcess = agentProcess,  
    action = action  
)  
  
// Bridge to your existing Flux Sink  
eventStream.subscribe { event ->  
    when {  
        event.isThinking() -> sink.next(YourEvent.fromThinking(event.getThinking()))  
        event.isObject() -> sink.next(YourEvent.fromObject(event.getObject()))  
    }  
}
Option 2: Use StreamingPromptRunnerBuilder
val results = StreamingPromptRunnerBuilder(runner)  
    .withStreaming()  
    .withPrompt(prompt)  
    .createObjectStreamWithThinking(YourType::class.java)  
  
results  
    .doOnNext { event ->  
        if (event.isThinking()) {  
            // Handle thinking events  
        } else if (event.isObject()) {  
            // Handle object events  
        }  
    }  
    .subscribe()
How StreamingEvent Works
The StreamingJacksonOutputConverter processes LLM responses in JSONL format StreamingJacksonOutputConverter.kt:107-131 :

Thinking blocks: content → StreamingEvent.Thinking
JSON objects: {"field": "value"} → StreamingEvent.Object
The converter handles mixed content where LLMs can output both reasoning and structured data StreamingJacksonOutputConverter.kt:75-101 .

Integration Strategy
You have two approaches:

Single Sink: Bridge only LLM streaming events to your Flux Sink, ignore OutputChannel for streaming
Dual Sinks: Use OutputChannel for agent events (progress, messages) and separately bridge LLM streaming events
The documentation shows examples with reactive callbacks using doOnNext, doOnError, doOnComplete page.adoc:31-57 .

Notes
LLM streaming requires ChatClientLlmOperations - check supportsStreaming() first
The StreamingEvent mechanism is completely separate from OutputChannel - they serve different purposes
You can see real integration examples in the test files for both Ollama and OpenAI streaming LLMOllamaStreamingBuilderIT.java:165-219



embabel/embabel-agent
embabel-agent-api/src/main/kotlin/com/embabel/agent/spi/support/springai/streaming/StreamingChatClientOperations.kt


        )
    }
 
    override fun generateStream(
        messages: List<Message>,
        interaction: LlmInteraction,
        agentProcess: AgentProcess,
        action: Action?,
    ): Flux<String> {
        return doTransformStream(messages, interaction, null)
    }
 
    override fun <O> createObjectStream(
        messages: List<Message>,
        interaction: LlmInteraction,
        outputClass: Class<O>,
        agentProcess: AgentProcess,
        action: Action?,
    ): Flux<O> {
        return doTransformObjectStream(messages, interaction, outputClass, null)
    }
 
    override fun <O> createObjectStreamWithThinking(
        messages: List<Message>,
        interaction: LlmInteraction,
        outputClass: Class<O>,
        agentProcess: AgentProcess,
        action: Action?,
    ): Flux<StreamingEvent<O>> {
        return doTransformObjectStreamWithThinking(messages, interaction, outputClass, null)
    }
 
    override fun <O> createObjectStreamIfPossible(
        messages: List<Message>,


embabel/embabel-agent
embabel-agent-common/src/main/kotlin/com/embabel/common/ai/converters/streaming/StreamingJacksonOutputConverter.kt


     * Supports both object lines and thinking blocks.
     * Uses resilient error handling - logs warnings for individual line failures but continues processing.
     */
    fun convertStreamWithThinking(text: String): Flux<StreamingEvent<T>> {
        return Flux.fromIterable(text.lines())
            .filter { it.isNotBlank() }
            .handle { line, sink ->
                try {
                    // Detect thinking state for the line
                    val thinkingState = ThinkingDetector.detectThinkingState(line)
 
                    when (thinkingState) {
                        ThinkingState.NONE -> {
                            // Line is JSON content
                            val result = super.convert(line)
                            if (result != null) {
                                sink.next(StreamingEvent.Object(result))
                            }
                        }
                        else -> {
                            // Line contains thinking content with detected state
                            val thinkingContent = ThinkingDetector.extractThinkingContent(line)
                            sink.next(StreamingEvent.Thinking(thinkingContent, thinkingState))
                        }
                    }
                } catch (e: Exception) {
                   sink.error(e)
                }
            }
    }
 
    /**
     * Override format to request JSONL instead of single JSON.
     * Inherits schema injection from parent but modifies instructions for streaming.
     */
    override fun getFormat(): String =
        """|
           |Your response should be in JSONL (JSON Lines) format.
           |Each line must contain exactly one JSON object that strictly adheres to the provided schema.
           |Do not include any explanations in the JSON objects themselves.
           |Do not include markdown code blocks or wrap responses in arrays.
           |Ensure RFC7464 compliant JSON Lines, one valid JSON object per line.
           |
           |You may include reasoning content using thinking blocks.
           |Use EXACTLY the <think> tag format - do not use variations like <thinking>, <thought>, or <analysis>.
           |<think>your reasoning here
           |another line of thinking</think>
           |
           |Thinking blocks are separate from JSON objects and can appear before, between, or after JSON lines as needed for your analysis.
           |
           |Here is the JSON Schema instance each JSON object must adhere to:
           |```${jsonSchema}```
           |
           |Example format:
           |<think>analyzing the requirements</think>
           |{"field": "precise_value"}
           |<think>considering next item</think>
           |{"field": "another_precise_value"}
           |""".trimMargin()
}

embabel/embabel-agent
embabel-agent-docs/src/main/asciidoc/reference/streaming/page.adoc


                .withPrompt(prompt)
                .createObjectStreamWithThinking(MonthItem.class);
        // Subscribe with real reactive callbacks using builder pattern
        results
                .timeout(Duration.ofSeconds(150))
                .doOnSubscribe(subscription -> {
                    logger.info("Stream subscription started");
                })
                .doOnNext(event -> {
                    if (event.isThinking()) {
                        String content = event.getThinking();
                        receivedEvents.add("THINKING: " + content);
                        logger.info("Integration test received thinking: {}", content);
                    } else if (event.isObject()) {
                        MonthItem obj = event.getObject();
                        receivedEvents.add("OBJECT: " + obj.getName());
                        logger.info("Integration test received object: {}", obj.getName());
                    }
                })
                .doOnError(error -> {
                    errorOccurred.set(error);
                    logger.error("Integration test stream error: {}", error.getMessage());
                })
                .doOnComplete(() -> {
                    completionCalled.set(true);
                    logger.info("Integration test stream completed successfully");
                })
                .blockLast(Duration.ofSeconds(6000));
----
==== Example - Simple Raw Text Streaming with Callbacks
[source,java]


embabel/embabel-agent
embabel-agent-autoconfigure/models/embabel-agent-ollama-autoconfigure/src/test/java/com/embabel/agent/config/models/ollama/LLMOllamaStreamingBuilderIT.java


    }
 
    @Test
    void realStreamingOllamaIntegrationWithReactiveCallbacks() {
        // Enable Reactor debugging
        reactor.util.Loggers.useVerboseConsoleLoggers();
 
        // Given: Use the existing streaming test LLM (configured as "best")
        PromptRunner runner = ai.withLlm("qwen3:latest")
                                .withToolObject(Tooling.class);
        assertTrue(runner.supportsStreaming(), "Test LLM should support streaming");
 
        // When: Subscribe with real reactive callbacks using builder pattern
        List<String> receivedEvents = new CopyOnWriteArrayList<>();
        AtomicReference<Throwable> errorOccurred = new AtomicReference<>();
        AtomicBoolean completionCalled = new AtomicBoolean(false);
 
        String prompt = "What are exactly two the most hottest months in Florida and their respective highest temperatures";
 
        // Use StreamingPromptBuilder instead of Kotlin extension function
        Flux<StreamingEvent<MonthItem>> results = new StreamingPromptRunnerBuilder(runner)
                .withStreaming()
                .withPrompt(prompt)
                .createObjectStreamWithThinking(MonthItem.class);
 
        results
                .timeout(Duration.ofSeconds(150))
                .doOnSubscribe(subscription -> {
                    logger.info("Stream subscription started");
                })
                .doOnNext(event -> {
                    if (event.isThinking()) {
                        String content = event.getThinking();
                        receivedEvents.add("THINKING: " + content);
                        logger.info("Integration test received thinking: {}", content);
                    } else if (event.isObject()) {
                        MonthItem obj = event.getObject();
                        receivedEvents.add("OBJECT: " + obj.getName());
                        logger.info("Integration test received object: {}", obj.getName());
                    }
                })
                .doOnError(error -> {
                    errorOccurred.set(error);
                    logger.error("Integration test stream error: {}", error.getMessage());
                })
                .doOnComplete(() -> {
                    completionCalled.set(true);
                    logger.info("Integration test stream completed successfully");
                })
                .blockLast(Duration.ofSeconds(6000));
 
        // Then: Verify real integration streaming behavior
        assertNull(errorOccurred.get(), "Integration streaming should not produce errors");
        assertTrue(completionCalled.get(), "Integration stream should complete successfully");
        assertFalse(receivedEvents.isEmpty(), "Should receive object events");
 
        logger.info("Integration streaming test completed successfully with {} total events", receivedEvents.size());
    }
 
    @Test
    void rawTextStreamingOllamaIntegrationWithReactiveCallbacks() {

embabel/embabel-agent
do I need to use state objects in embabel to build agentic work flows? or they are optional? whendo state objects (@State) like class annototated with @State or actions annotated with @State are help ...
Show full text
Fast
View as codemap
State objects (@State classes) are optional in Embabel - you can build complete agentic workflows without them. They're a powerful tool for specific patterns but not required for most use cases.

When @State Classes Are Helpful
@State classes excel at complex workflows that need:

1. Looping Patterns
For revise-and-review cycles or iterative processing where you need to return to a previous state type page.adoc:69-95 :

@State  
record ProcessingState(String data, int iteration) {  
    @Action(clearBlackboard = true)  // Enables looping  
    LoopOutcome process() {  
        if (iteration >= 3) {  
            return new DoneState(data);  
        }  
        return new ProcessingState(data + "+", iteration + 1);  
    }  
}
2. Branching Workflows
When decisions lead to different processing paths page.adoc:155-202 :

@State  
interface Stage {}  
  
record AssessStory(String content) implements Stage {  
    @Action  
    Stage assess() {  
        if (isAcceptable()) {  
            return new Done(content);  
        } else {  
            return new ReviseStory(content);  
        }  
    }  
}
3. Human-in-the-Loop Processes
For workflows that pause for user input using WaitFor page.adoc:407-432 :

@State  
record AssessStory(Story story) {  
    @Action  
    HumanFeedback getFeedback() {  
        return WaitFor.formSubmission("Please review", HumanFeedback.class);  
    }  
}
4. Complex Multi-Stage Processes
When workflows have discrete phases that need clear boundaries page.adoc:29-38 .

When @State Classes Are Overkill
Avoid states for simple scenarios:

1. Single-Action Tasks
@Agent(description = "Simple processor")  
public class SimpleProcessor {  
    @AchievesGoal(description = "Process input")  
    @Action  
    public Output process(Input input) {  
        return new Output(input.value().toUpperCase());  
    }  
}
2. Linear Transformation Chains
When actions naturally flow from output to input without branching:

@Action  
public ValidatedData validate(RawData data) { ... }  
  
@Action    
public ProcessedData process(ValidatedData data) { ... }  
  
@Action  
public FinalOutput finalize(ProcessedData data) { ... }
3. Simple Chatbots
Basic question-answering without complex flow control page.adoc:470-484 .

Key Requirements for @State Classes
If you use states, they must be:

Static nested classes (Java) or top-level classes (Kotlin) page.adoc:460-486
Non-static inner classes are rejected to prevent serialization issues AgentMetadataReader.kt:368-389
Alternative: Regular @Action Methods
For most workflows, regular @Action methods with GOAP planning are sufficient page.adoc:268-269 :

Types constrain composition (deterministic but rigid)
Planner finds optimal sequence automatically
No explicit state management needed
Decision Guide
Use Case    Recommended Approach
Simple input → output transformation    Regular @Action methods
Multi-step linear process   Regular @Action methods
Looping/iteration required  @State with clearBlackboard = true
Branching based on conditions   @State with parent interface
Human approval needed   @State with WaitFor
Complex workflow with phases    @State for clarity
Notes
State transitions hide previous state objects but preserve non-state context page.adoc:20-25
Actions can return this to stay in the same state (requires canRerun = true) page.adoc:40-67
The @State annotation is inherited through class hierarchies page.adoc:112-137
Wiki pages you might want to explore:

Actions, Goals, and Conditions (embabel/embabel-agent)
-----------------------------------------------------------------------
I have a chatbot application where I check first the account status. if account is closed, suspended or cancelled, I have to send a message to customer with a message. and then I have to check if cuto...
Show full text
Fast
View as codemap
For your chatbot workflow with multiple conditional checks, I recommend using Embabel's @State pattern with a parent interface for clean branching logic.

Design Overview
@Agent(description = "Customer support troubleshooting chatbot")  
class SupportChatbot {  
      
    // Parent state interface for all workflow stages  
    @State  
    interface SupportStage {}  
      
    // Entry action that starts the workflow  
    @Action  
    SupportStage checkAccountStatus(CustomerQuery query) {  
        return new AccountCheck(query);  
    }  
      
    // State for account status validation  
    @State  
    record AccountCheck(CustomerQuery query) implements SupportStage {  
        @Action  
        SupportStage validateAccount() {  
            AccountStatus status = getAccountStatus(query.customerId());  
              
            if (status.isClosed() || status.isSuspended() || status.isCancelled()) {  
                return new AccountClosed(query, status);  
            }  
            return new CustomerTypeCheck(query, status);  
        }  
    }  
      
    // Terminal state for closed accounts  
    @State  
    record AccountClosed(CustomerQuery query, AccountStatus status) implements SupportStage {  
        @AchievesGoal(description = "Handle closed account")  
        @Action  
        SupportResponse handleClosed() {  
            String message = "Your account is " + status.getStatus() +   
                           ". Please contact support for assistance.";  
            return new SupportResponse(message);  
        }  
    }  
      
    // State for customer type validation  
    @State  
    record CustomerTypeCheck(CustomerQuery query, AccountStatus status) implements SupportStage {  
        @Action  
        SupportStage checkCustomerType() {  
            CustomerType type = getCustomerType(query.customerId());  
              
            if (type.isBroadband()) {  
                return new BroadbandMessage(query, type);  
            }  
            return new OutageCheck(query, status, type);  
        }  
    }  
      
    // Terminal state for broadband customers  
    @State  
    record BroadbandMessage(CustomerQuery query, CustomerType type) implements SupportStage {  
        @AchievesGoal(description = "Handle broadband customer")  
        @Action  
        SupportResponse handleBroadband() {  
            String message = "Broadband support is handled through a different channel. " +  
                           "Please call our broadband support line.";  
            return new SupportResponse(message);  
        }  
    }  
      
    // State for outage checking  
    @State  
    record OutageCheck(CustomerQuery query, AccountStatus status, CustomerType type) implements SupportStage {  
        @Action  
        SupportStage checkOutage() {  
            boolean hasOutage = checkServiceOutage(query.serviceArea());  
              
            if (hasOutage) {  
                return new OutageResponse(query);  
            }  
            return new Troubleshooting(query, status, type);  
        }  
    }  
      
    // Terminal state for outage situations  
    @State  
    record OutageResponse(CustomerQuery query) implements SupportStage {  
        @AchievesGoal(description = "Handle service outage")  
        @Action  
        SupportResponse handleOutage() {  
            String message = "We're currently experiencing an outage in your area. " +  
                           "Our team is working on it. We'll notify you when service is restored.";  
            return new SupportResponse(message);  
        }  
    }  
      
    // Final state for troubleshooting  
    @State  
    record Troubleshooting(CustomerQuery query, AccountStatus status, CustomerType type) implements SupportStage {  
        @AchievesGoal(description = "Proceed with troubleshooting")  
        @Action  
        SupportResponse startTroubleshooting() {  
            // Run provisioning checks and other troubleshooting steps  
            TroubleshootingResult result = runProvisioningCheck(query);  
            return new SupportResponse(result.getMessage());  
        }  
    }  
}
Key Design Benefits
Clear Branching Logic: Each decision point is a separate state with a single responsibility page.adoc:155-202

Polymorphic Transitions: Actions can return any SupportStage implementation, allowing dynamic routing based on conditions

Terminal States: Each endpoint (closed account, broadband, outage, troubleshooting) is clearly marked with @AchievesGoal

Type Safety: The compiler ensures all possible states are handled

Alternative: BranchingAction Pattern
For simpler cases, you could use BranchingAction:

@Action  
Branch<AccountClosed, CustomerTypeCheck> checkAccount(CustomerQuery query) {  
    AccountStatus status = getAccountStatus(query.customerId());  
    if (status.isClosed()) {  
        return Branch.left(new AccountClosed(query, status));  
    }  
    return Branch.right(new CustomerTypeCheck(query, status));  
}
However, the @State pattern is more readable for complex multi-step workflows like yours BranchingAction.kt:24-42 .

Notes
State classes must be static nested classes (Java) or top-level classes (Kotlin) page.adoc:460-486
The @State annotation on the parent interface automatically applies to all implementing classes page.adoc:112-137
For chatbots, consider using Utility AI planner for more flexible behavior page.adoc:26-35
Wiki pages you might want to explore:

DSL-Based Agent Definition (embabel/embabel-agent)

