in my chatbot application, everytime an action is processed, we are storing data manually into blackboard (mongo based). and when the next turn comes, it tries to run same action again even thought th...
Show full text
Fast
View as codemap
Your approach of manually checking for action results in the blackboard is not the standard Embabel pattern. The framework provides built-in mechanisms to handle this scenario more elegantly.

The Issue with Your Current Approach
You're manually storing data and checking for presence to prevent re-execution, but Embabel already handles this through:

Automatic hasRun tracking: Actions automatically get a hasRun condition set after execution AbstractAgentProcess.kt:388-400
canRerun attribute: Controls whether actions can execute multiple times (defaults to false) page.adoc:35-36
Recommended Solutions
Option 1: Use canRerun = false (Default)
For account details that should only be looked up once per session:

@Action  // canRerun defaults to false  
public AccountDetails getAccountDetails(CustomerQuery query) {  
    // This will only run once per process  
    return accountService.lookup(query.getCustomerId());  
}
Option 2: Use Conversation Interface for Chat Context
For chatbot-specific data that should persist across messages page.adoc:84-97 :

@Action(canRerun = true, trigger = UserMessage.class)  
public Response handleMessage(UserMessage message, Conversation conversation) {  
    // Check if account details already exist in conversation  
    AccountDetails details = conversation.getAsset(AccountDetails.class);  
    if (details == null) {  
        details = accountService.lookup(extractCustomerId(message));  
        conversation.addAsset(details);  
    }  
    // Use details for response  
}
Option 3: Use ContextRepository for Cross-Process Persistence
For data that should survive beyond a single process page.adoc:185-195 :

// When creating the chatbot session  
ProcessOptions options = new ProcessOptions()  
    .withContextId("customer-" + customerId);  
  
// The context will automatically populate the blackboard  
@Action  
public AccountDetails getAccountDetails(Context context) {  
    // Context data is already available from previous sessions  
    return context.get(AccountDetails.class);  
}
Why Your Manual Approach is Problematic
Race conditions: Manual checks can have timing issues
Code complexity: Adds unnecessary conditional logic
Framework bypass: You're working against Embabel's design
Maintenance burden: Manual state management is error-prone
Key Insight
The blackboard is designed to be automatically managed by the framework page.adoc:81-83 . You should rely on Embabel's built-in state management rather than implementing your own tracking logic.

For your account details lookup specifically, use canRerun = false (the default) and let the framework handle the one-time execution. The result will remain on the blackboard for the duration of the session.

Notes
The hasRun condition is automatically set for ALL actions, not just those with canRerun = false AbstractAgentProcess.kt:389-393
Consider using the Conversation interface for chat-specific context rather than manual blackboard storage
If you need persistence across server restarts, implement a custom ContextRepository page.adoc:193-195
Wiki pages you might want to explore:

Architecture Overview (embabel/embabel-agent)
-----------------------------------
does embabel framework offer context management techniques out of the box or its developer responsibility to create these techniques?
Fast
View as codemap
Embabel provides several context management techniques out of the box, covering different scopes and use cases.

Built-in Context Management Techniques
1. Blackboard System (Process-level Context)
The Blackboard serves as the primary context mechanism during agent execution, storing all domain objects, intermediate results, and process state page.adoc:76-91 . It provides:

Type-based access to objects
Ordered storage with latest-first retrieval
Condition tracking for planning
Automatic binding of action inputs/outputs
2. Context Persistence (Cross-process Context)
For longer-term state that persists across multiple agent processes, Embabel offers the Context class page.adoc:185-195 :

Identified by unique contextId string
Populates process blackboard when starting a new process
Default implementation is in-memory only
Requires custom ContextRepository for persistent storage
3. State Management (@State Classes)
For workflow-level context in complex processes page.adoc:470-483 :

State objects automatically persisted in blackboard
Actions can depend on specific state presence
State transitions drive workflow flow
Context preserved across transitions (non-state objects remain available)
4. Conversation Context (Chat Sessions)
For chatbot applications page.adoc:84-97 :

Conversation interface holds message history
Asset tracking for generated content
Managed by ChatSession implementations
Stored in agent process blackboard
5. Process Context (Execution Environment)
Each agent process has a ProcessContext containing ProcessContext.kt:28-39 :

Process options and configuration
Platform services (LLM operations, event listeners)
Output channel for messaging
Reference to the agent process and blackboard
Developer Responsibilities
While Embabel provides these mechanisms, developers are responsible for:

Implementing ContextRepository if you need persistent cross-process context beyond the default in-memory implementation page.adoc:193-195

Designing appropriate data structures for your specific context needs (e.g., what to store in @State classes or Context)

Managing context lifecycle - deciding when to clear blackboard (clearBlackboard = true) for loops or context reset page.adoc:45-54

Notes
The blackboard is the core context mechanism and is automatically managed by the framework page.adoc:81-83
State transitions hide previous state objects but preserve non-state context across transitions page.adoc:20-25
For most use cases, the built-in mechanisms are sufficient - only implement custom persistence when needed
Wiki pages you might want to explore:

User Interfaces (embabel/embabel-agent)
