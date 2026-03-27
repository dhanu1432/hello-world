Budget


how is budget used in embabel? can we set token limit? how does token limit play while running actions that use LLM
Fast
View as codemap
Budget in Embabel controls resource limits and process termination through the Budget class, which enforces cost, action count, and token limits during agent execution.

Quick Answer
Yes, you can set token limits. The Budget class includes a tokens property (default: 1,000,000) that terminates the process when exceeded. Token limits are enforced by tracking total usage across all LLM calls in the process.

Detailed Explanation
Budget Configuration
The Budget class controls three resource limits ProcessOptions.kt:120-158 :

data class Budget @JvmOverloads constructor(  
    val cost: Double = DEFAULT_COST_LIMIT,      // Default: $2.00  
    val actions: Int = DEFAULT_ACTION_LIMIT,    // Default: 50 actions  
    val tokens: Int = DEFAULT_TOKEN_LIMIT       // Default: 1,000,000 tokens  
)
Token Limit Enforcement
Token limits work through the early termination system:

Tracking: Each LLM invocation tracks token usage in LlmInvocation LlmInvocation.kt:54-58
Aggregation: Total usage is summed across all LLM calls in the process
Termination: MaxTokensEarlyTerminationPolicy checks if total tokens >= limit and terminates if exceeded EarlyTerminationPolicy.kt:141-154
How Budget Integrates with Actions
When you create an agent process, the budget creates an early termination policy ProcessOptions.kt:126-132 :

fun earlyTerminationPolicy(): EarlyTerminationPolicy {  
    return EarlyTerminationPolicy.firstOf(  
        EarlyTerminationPolicy.maxActions(maxActions = actions),  
        EarlyTerminationPolicy.maxTokens(maxTokens = tokens),  
        EarlyTerminationPolicy.hardBudgetLimit(budget = cost)  
    )  
}
This policy is automatically applied to the process and checked after each action execution.

Setting Custom Token Limits
// Create custom budget with token limit  
Budget budget = new Budget()  
    .withCost(5.0)      // $5.00 cost limit  
    .withActions(100)   // 100 action limit  
    .withTokens(500000); // 500,000 token limit  
  
// Apply to process  
ProcessOptions options = new ProcessOptions()  
    .withBudget(budget);  
  
AgentProcess process = agentPlatform.createAgentProcess(agent, options, bindings);
Token Usage During LLM Actions
When actions use LLM operations:

Each call to the LLM creates an LlmInvocation with usage data
The framework sums prompt and completion tokens across all calls
The running total is checked against the budget limit after each action
If exceeded, the process terminates with an error
Notes
Token limits apply to the entire process, not individual LLM calls
The framework tracks tokens across different LLM models and providers
Default token limit is 1,000,000 tokens - adjust based on your use case and model costs
Budget limits are a safety mechanism to prevent runaway costs in production EarlyTerminationPolicy.kt:101-109
Wiki pages you might want to explore:

Streaming and Extended Thinking (embabel/embabel-agent)




