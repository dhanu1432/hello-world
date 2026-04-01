what is the relation between simpleagentprocess, concurrentagentprocess and replanrequestedexception
Fast
View as codemap
SimpleAgentProcess and ConcurrentAgentProcess are both implementations of AgentProcess, with ConcurrentAgentProcess extending SimpleAgentProcess. ReplanRequestedException is a control flow mechanism that actions can throw to trigger replanning, and SimpleAgentProcess has specific logic to handle this exception.

Core Relationship
Inheritance Hierarchy






ConcurrentAgentProcess extends SimpleAgentProcess ConcurrentAgentProcess.kt:44-53 , inheriting its core planning and execution logic while adding concurrent action execution capabilities.

ReplanRequestedException Handling
SimpleAgentProcess has dedicated handling for ReplanRequestedException in its formulateAndExecutePlan method SimpleAgentProcess.kt:166-184 :

Catches the exception during action execution
Applies blackboard updates via rpe.blackboardUpdater.accept(blackboard)
Blacklists the action to prevent infinite loops with replanBlacklist.add(action.name)
Keeps process running to trigger replanning on next tick
Key Differences
SimpleAgentProcess
Executes actions sequentially (one at a time)
Has comprehensive ReplanRequestedException handling with blacklist mechanism
Uses replanBlacklist to prevent the same action from being selected repeatedly SimpleAgentProcess.kt:68
ConcurrentAgentProcess
Executes multiple actions concurrently using coroutines ConcurrentAgentProcess.kt:92-107
Overrides formulateAndExecutePlan but doesn't explicitly handle ReplanRequestedException
Relies on inherited exception handling from parent class
ReplanRequestedException Purpose
ReplanRequestedException is a control flow exception thrown by tools/actions to signal that the agent should replan based on updated state ReplanRequestedException.kt:32-48 :

// Example usage in a tool  
throw ReplanRequestedException(  
    reason = "Routing to alternate path",  
    blackboardUpdater = { bb -> bb["routedTo"] = "alternate" }  
)
Process Selection Logic
The DefaultAgentPlatform chooses between these implementations based on configuration DefaultAgentPlatform.kt:177-198 :

val agentProcess = when (processType) {  
    AgentPlatformProperties.ProcessType.SIMPLE -> SimpleAgentProcess(...)  
    AgentPlatformProperties.ProcessType.CONCURRENT -> ConcurrentAgentProcess(...)  
}
Notes
SimpleAgentProcess has robust replanning logic with blacklist to prevent infinite loops
ConcurrentAgentProcess inherits this logic but its concurrent execution may affect replanning behavior
ReplanRequestedException is intentionally propagated through the call stack (not suppressed) to trigger replanning ActionRunner.kt:65-68
The blacklist mechanism in SimpleAgentProcess is cleared after successful planning SimpleAgentProcess.kt:147
