I have a mongobasedblackboard implementing blackboard interface. I have agent_blackboard collection in mongo storing all intermediate data , contextId, processId, snapshots, conversation history etc. ...
Show full text
Fast
View as codemap
Your MongoDB-based blackboard and Embabel's ContextRepository serve different purposes in the framework architecture.

Quick Answer
MongoDB Blackboard: A persistent implementation of the Blackboard interface that stores process-specific data (including hasRun conditions) in MongoDB.

ContextRepository: Stores Context objects that can populate any blackboard across multiple processes. It's separate from the blackboard system.

The relationship: When creating a process with a contextId, the framework loads the Context from ContextRepository and populates it into your MongoDB blackboard DefaultAgentPlatform.kt:139-156 .

Detailed Explanation
Architecture Overview









Key Differences
Aspect	MongoDB Blackboard	ContextRepository
Scope	Single agent process	Multiple processes
Data	All process data including hasRun conditions	Only data explicitly saved to Context
Lifecycle	Created/destroyed with process	Persists independently
Purpose	Runtime execution state	Long-term data sharing
How They Work Together
Process Creation: When you specify a contextId in ProcessOptions , the framework:
Looks up the Context from ContextRepository InMemoryContextRepository.kt:44-46
Populates your MongoDB blackboard with the Context data DefaultAgentPlatform.kt:147-148
During Execution: Your MongoDB blackboard stores everything including:
Action results and intermediate data
hasRun conditions (preventing re-execution)
Process snapshots and conversation history
Process End: Data in your MongoDB blackboard remains, but Context is only updated if explicitly saved
Your Current Implementation
Your MongoDB blackboard is essentially a persistent blackboard implementation. The hasRun values you see are conditions stored on the blackboard to track which actions have executed . These are ephemeral to the process, not stored in Context.

Recommendation
Consider using both:

ContextRepository for data that should persist across processes (e.g., user preferences, account details)
MongoDB Blackboard for process-specific execution state
You could implement a MongoDB-based ContextRepository to match your blackboard persistence strategy.

Notes
The default ContextRepository is in-memory only page.adoc:193-195
Context and blackboard are independent systems - Context populates blackboard but doesn't replace it
Your MongoDB blackboard implementation is valid and useful for process persistence
Wiki pages you might want to explore:

Architecture Overview (embabel/embabel-agent)
----------------------------
do I need to return contextId to client so they can send it every time in multi turn conversation? using contextId how do I initiate the agent? how does framework know which agent has worked on this? ...
Show full text
Fast
View as codemap
Yes, you need to return the contextId to the client for multi-turn conversations. The contextId enables data persistence across multiple agent processes, but it doesn't track which agent was used.

Using contextId in Multi-Turn Conversations
1. Returning contextId to Client
When creating an agent process, generate or use a contextId and return it to the client:

// First turn - create context  
String contextId = "customer-" + customerId;  
ProcessOptions options = new ProcessOptions()  
    .withContextId(contextId);  
  
AgentProcess process = agentPlatform.createAgentProcess(agent, options, bindings);  
return new ChatResponse(process.getId(), contextId);
2. Initiating Agent with contextId
On subsequent turns, use the same contextId to restore the blackboard state DefaultAgentPlatform.kt:139-156 :

// Subsequent turns - use existing context  
ProcessOptions options = new ProcessOptions()  
    .withContextId(clientContextId);  
  
AgentProcess process = agentPlatform.createAgentProcess(sameAgent, options, newBindings);
3. How Context Loading Works
When you specify a contextId in ProcessOptions ProcessOptions.kt:210-225 , the framework:

Looks up the context from ContextRepository InMemoryContextRepository.kt:44-46
Populates the new process's blackboard with stored data DefaultAgentPlatform.kt:147-148
The agent then operates on this restored state
Important Clarifications
Agent Assignment is Manual
The framework does not track which agent worked on a context. You must specify the same agent when creating new processes with the same contextId. The context only stores data, not agent information.

Context vs Agent Process
Context: Persistent data storage across processes (in-memory by default) page.adoc:193-195
Agent Process: Single execution instance with its own blackboard
contextId: Links multiple processes to shared data
For Chatbot Applications
Consider using the Conversation interface instead of raw context management page.adoc:84-97 . The AgentProcessChatbot handles long-lived processes automatically AgentProcessChatbot.kt:67-90 .

Notes
Default ContextRepository is in-memory only - implement a persistent version for production use
Context data is loaded into the blackboard at process creation, not streamed during execution
The same agent class must be used for all processes sharing a context to ensure compatibility
Wiki pages you might want to explore:

Architecture Overview (embabel/embabel-agent)
Wiki pages you might want to explore:

Architecture Overview (embabel/embabel-agent)
