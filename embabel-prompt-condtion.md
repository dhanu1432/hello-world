explain me what is a prompt based condition in embabel and where this is useful while building agents
Fast
View as codemap
A prompt-based condition in Embabel is a condition that uses an LLM to evaluate whether a condition is true or false, rather than using code-based logic PromptCondition.kt:31-43 .

What is a Prompt-Based Condition?
A prompt-based condition (PromptCondition) prompts an LLM to evaluate a condition based on the current context. It takes a prompt function that generates the evaluation prompt and an LlmCall configuration PromptCondition.kt:39-43 . When evaluated, it makes an LLM call and returns a ConditionDetermination based on the LLM's response PromptCondition.kt:52-78 .

How to Create Prompt-Based Conditions
You can create prompt-based conditions using the promptedCondition method in the DSL:

val meetsQualityStandards by promptedCondition(  
    name = "qualityCheck",  
    prompt = { context ->  
        val content = context.processContext.blackboard  
            .getValue("content", Content::class.java)  
        """  
        Evaluate if this content meets quality standards:  
        ${content.text}  
          
        Return true if it's well-written, clear, and professional.  
        """  
    },  
    llm = LlmCall(  
        options = LlmOptions().withTemperature(0.2)  
    )  
)
AgentBuilder.kt:301-317

When to Use Prompt-Based Conditions
Prompt-based conditions are useful when:

Natural language understanding is required - When evaluating semantic content, sentiment, or quality that's difficult to express in code
Complex logic would be brittle - When the evaluation logic is complex and would be fragile to implement in code
Subjective assessments - For quality checks, sentiment analysis, or content appropriateness
Example Use Cases
Quality Check:

val contentMeetsStandards by promptedCondition(  
    prompt = { context ->  
        val article = context.processContext.blackboard.getValue("article", Article::class.java)  
        """  
        Evaluate if this article meets publishing standards:  
        Title: ${article.title}  
        Content: ${article.content}  
          
        Consider: clarity, grammar, factual accuracy, and appropriate tone.  
        """  
    }  
)
Sentiment Analysis:

val isPositiveSentiment by promptedCondition(  
    prompt = { context ->  
        val review = context.processContext.blackboard.getValue("review", Review::class.java)  
        """  
        Analyze the sentiment of this review:  
        ${review.text}  
          
        Return true if the sentiment is positive.  
        """  
    }  
)
Cost Considerations
Prompt-based conditions are expensive to evaluate (cost = 1.0) because they require LLM calls PromptCondition.kt:50 . Use them sparingly and prefer code-based conditions (conditionOf) when the logic can be expressed deterministically AgentBuilder.kt:272-294 .

Notes
Prompt-based conditions return a Determination object with result, confidence, and explanation fields PromptCondition.kt:82-91
The framework automatically formats the evaluation prompt to request structured output from the LLM PromptCondition.kt:54-58
Multiple prompt runners implement evaluateCondition methods that follow the same pattern of prompting the LLM for structured evaluation OperationContextPromptRunner.kt:185-213
Wiki pages you might want to explore:

Multi-Agent Collaboration (embabel/embabel-agent)
DSL-Based Agent Definition (embabel/embabel-agent)
