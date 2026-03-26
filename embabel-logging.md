In embabel, is there a way to set contextId to logs for all actions? looking for a central location where I can just set or configure so all the logs get printed with same contextId. I see logs get pr...
Show full text
Fast
View as codemap
Based on the codebase, Embabel's logging system is designed to log processId rather than contextId. These serve different purposes:

processId: Unique identifier for each AgentProcess instance, used in logging
contextId: Identifier for persisting state across multiple process runs page.adoc:190-192
Current Logging Behavior
All log messages in Embabel's LoggingAgenticEventListener use processId from events, not contextId LoggingAgenticEventListener.kt:213-300 . This is by design - each process execution gets its own unique identifier for tracking.

Why You See threadId=None
The "threadId=None" you're seeing likely comes from Spring's default logging pattern, not Embabel's logging. Embabel's personality-based logging (like Star Wars) uses processId in its formatted messages StarWarsLoggingAgenticEventListener.kt:92-134 .

Solutions
Option 1: Custom Logging Listener
Create a custom AgenticEventListener that includes contextId in log messages:

class ContextAwareLoggingListener : LoggingAgenticEventListener() {  
    override fun getActionExecutionStartMessage(e: ActionExecutionStartEvent): String =  
        "[${e.processId}|ctx:${e.agentProcess.processOptions.contextId}] executing action ${e.action.name}"  
}
Option 2: Configure Logging Pattern
Update your application.yml to include context information from MDC:

logging:  
  pattern:  
    console: "%clr(%d{HH:mm:ss.SSS}){faint} %clr([%X{contextId:-none}]){blue} %clr(%-5level) %clr(%logger{0}){cyan} %clr(-){faint} %msg%n"
Option 3: Use ProcessOptions with Context
Ensure you're setting contextId when creating processes:

val options = ProcessOptions.DEFAULT  
    .withContextId("my-context-id")
Notes
The processId and contextId serve different purposes - processId tracks individual executions, contextId enables state persistence across runs
Embabel's built-in logging personalities cannot be easily modified to include contextId without creating a custom listener
The contextId is properly stored in ProcessOptions and accessible via agentProcess.processOptions.contextId if you need it in custom code
Wiki pages you might want to explore:

Annotation-Based Agent Definition (embabel/embabel-agent)
