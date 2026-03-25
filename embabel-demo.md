logging theme:
Multiple Profiles
You can combine the logging theme profile with other profiles:

spring:
  profiles:
    active: dev,logging-theme-matrix

-----------
Key Code Entities
Code                                           Entity	Type	              Purpose
Agent.asTransformation<I,O>()	                Extension function	      Converts Agent to Transformation<I,O>
Agent.asAction<I,O>()	                        Extension function	      Converts Agent to Action interface
AgentBuilder.localAgentAction<I,O>(agent)	    DSL method	              Embeds agent as private action
AgentBuilder.referencedAgentAction<I,O>(name)	DSL method	              References deployed agent by name
AgentPlatform.createChildProcess()	          Method	                  Creates nested AgentProcess
AgentProcess.resultOfType<T>()	              Method	                  Extracts typed result from child
---------------------

Comparison
Aspect	          Local Agent	                          Referenced Agent
Registration	    Private, not in global registry	      Must be deployed to AgentPlatform
Reusability	      Single parent only	                  Shared across multiple agents
Lookup overhead	  None (direct reference)	                Runtime lookup by name
Error handling	  Compile-time type safety	              Runtime IllegalArgumentException if not found
Use case	        Task-specific sub-agents	                Shared utility agents
--------------------------------------------------
agent dicsovery: agent calls /a2a/agents to get agent metadata and picks agent
------------------------
Goal Choice Approver to filter out state goals
-----------------------
Supervisor Planner allows single goal type
----------------------
Dynamic Replan exception and flow restart.
what features or procedures embabel offers to restart work flow at a random point based on intent detection and how do I pick a random action based on what user is asking and process it and go back to...
Show full text
Fast
View as codemap
Summary
Embabel provides several mechanisms for dynamic workflow control and topic switching: ReplanRequestedException for intent-based replanning, @State annotations for topic transitions, Utility AI for flexible action selection, and the blackboard system for context preservation. These can be combined to create resilient agents that handle topic switching naturally.

Key Features for Dynamic Workflow Control
1. Intent-Based Replanning with ReplanRequestedException
Actions can trigger immediate replanning based on detected intent by throwing ReplanRequestedException with blackboard updates SimpleAgentProcessTest.kt:140-144 :

throw ReplanRequestedException(  
    reason = "Routing to alternate path",  
    blackboardUpdater = { bb -> bb["routedTo"] = "alternate" }  
)
This allows the agent to:

Detect user intent changes mid-flow
Update context with new information
Trigger immediate replanning from the new state
2. State-Based Topic Switching
The @State annotation enables clean topic transitions by hiding previous state objects and binding new ones page.adoc:13-21 :

Previous state objects are hidden from planning
New state objects are bound to the blackboard
Non-state objects (conversation history, user data) remain available
Planner considers only actions from the new state
3. Utility AI for Flexible Action Selection
Utility AI selects the highest-value action at each step rather than following a fixed plan page.adoc:33-34 , making it ideal for:

Responding to changing user intent
Handling multiple valid response strategies
Dynamic cost-based action selection with @Cost methods page.adoc:318-322
4. Long-Lived Chatbot Processes
Chatbots use long-lived AgentProcess instances that maintain state across messages page.adoc:15-24 :

Same process responds to multiple user messages
Blackboard maintains session state
Actions can be triggered by various events, not just user input
Implementation Pattern for Resilient Topic Switching
Combining States with Utility AI
@State  
record TopicAState(String context) {  
    @Action(canRerun = true, trigger = UserMessage.class)  
    TopicAState handleUserMessage(UserMessage msg, ActionContext ctx) {  
        // Detect intent to switch topics  
        if (shouldSwitchTopic(msg)) {  
            throw ReplanRequestedException(  
                reason = "Switching to Topic B",  
                blackboardUpdater = { bb ->   
                    bb["previousTopic"] = "TopicA"  
                    bb["topicAContext"] = this.context  
                }  
            );  
        }  
        return this; // Stay in current state  
    }  
}  
  
@State    
record TopicBState(String previousContext) {  
    @Action(canRerun = true, trigger = UserMessage.class)  
    TopicBState handleWithReturnPath(UserMessage msg, Blackboard bb) {  
        // Can access previous topic context from blackboard  
        String previousTopic = bb["previousTopic"];  
        if (shouldReturnToPrevious(msg)) {  
            return new TopicAState(bb["topicAContext"]);  
        }  
        return this;  
    }  
}
Context Preservation Strategies
Explicit Context Passing: Store previous topic data in state records when using clearBlackboard = true page.adoc:435-444
Blackboard Persistence: Non-state objects remain available across state transitions page.adoc:20-24
Conversation History: Use the Conversation interface to maintain message history page.adoc:86-90
Making Agents Resilient
Error Recovery with Replanning
The ReplanRequestedException mechanism allows agents to recover from unexpected situations by SimpleAgentProcessTest.kt:158-166 :

Detecting when current approach isn't working
Updating the blackboard with new information
Triggering replanning without losing context
Dynamic Cost Adjustment
Use @Cost methods to adjust action selection based on context page.adoc:318-322 :

@Cost  
double dynamicCost(Blackboard bb) {  
    // Increase cost of actions in current topic if user seems frustrated  
    return bb.contains("userFrustrated") ? 100 : 10;  
}
Notes
Embabel doesn't have true "random" restarts but provides deterministic mechanisms for dynamic replanning based on intent
The combination of @State, ReplanRequestedException, and Utility AI provides a powerful framework for handling topic switching
Context preservation is automatic for non-state objects but must be explicitly managed when using clearBlackboard = true
The chatbot architecture (AgentProcessChatbot) provides a ready-made pattern for long-lived conversational agents
Wiki pages you might want to explore:
-----------------------------------------
AgentPlatform Overview
The AgentPlatform is the central runtime component that manages agent deployment and execution. It serves as a registry for agents and a factory for agent processes.

Key Responsibilities
Responsibility	Methods	Description
Agent Registry	deploy(), agents()	Maintains deployed agents and makes them available for execution
Process Management	createAgentProcess(), runAgentFrom(), getAgentProcess(), killAgentProcess()	Creates, tracks, and manages agent process lifecycles
AgentScope Interface	actions, goals, conditions, domainTypes	Aggregates capabilities of all deployed agents
Child Process Creation	createChildProcess()	Enables nested agent execution with blackboard inheritance
-------------------------------------------
Agent Process Lifecycle
An AgentProcess is the runtime execution context for an agent, managing state transitions, action execution, and event publication throughout its lifetime.
Process Creation
Creation by AgentPlatform
The AgentPlatform is responsible for creating and managing AgentProcess instances. Process creation occurs through two primary methods:

Root Process Creation: AgentPlatform.createAgentProcess() creates a new top-level process
Child Process Creation: AgentPlatform.createChildProcess() creates a subprocess from a parent
Process States and Status Codes
An AgentProcess transitions through a well-defined set of states during its lifetime. The status is tracked using AgentProcessStatusCode enumeration (stored in an AtomicReference for thread safety) and reflected in the AgentProcessStatusReport.

Status Codes
Status Code	Description	Terminal State
NOT_STARTED	Process has been instantiated but not yet started	No
RUNNING	Process is actively executing actions and planning	No
COMPLETED	Process successfully achieved its goal	Yes
FAILED	Process encountered an error during execution	Yes
WAITING	Process is paused awaiting external input (human-in-the-loop)	No
PAUSED	Process has been paused for scheduled execution	No
STUCK	Planning system cannot find a valid path to the goal	No*
KILLED	Process was forcibly terminated via kill()	Yes
TERMINATED	Process was terminated by an early termination policy	Yes
-------------------
Primary implementations:

MultiTransformationAction: Actions from @Action-annotated methods (
embabel-agent-api/src/main/kotlin/com/embabel/agent/api/common/support/MultiTransformationAction.kt
34-170
)
TransformationAction: Single-input DSL transformations (
embabel-agent-api/src/main/kotlin/com/embabel/agent/api/common/support/TransformationAction.kt
30-95
)
BranchingAction: Actions that can return one of two types (
embabel-agent-api/src/main/kotlin/com/embabel/agent/api/common/support/BranchingAction.kt
48-121
)
