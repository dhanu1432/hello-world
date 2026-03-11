https://medium.com/@springrod/embabel-year-end-update-building-the-best-agent-framework-25ed98728e79

A2A protocol — each agent goal is exported with @Export(remote = true), auto-discoverable at /.well-known/agent.json

How @Export(remote = true) Works on Sub-Agents
In Embabel, @Export(remote = true) is placed on each agent's own @AchievesGoal, including sub-agents. The framework has three working examples that prove this:

Agent	Is a Sub-Agent?	Has @Export(remote=true)?

StarNewsFinder
✅ Used by 

Handoff
 and 

Subagents
✅ Yes

FactChecker
✅ Can be used as subagent	✅ Yes

BookWriter
✅ Standalone	✅ Yes
This gives you dual access: the sub-agent is callable both in-process (via Subagent.ofClass() from the supervisor) and remotely (via A2A from any external client).

The implementation plan already has this correctly — each of the 4 agents (supervisor, mobility, broadband, education) exports its own goal. That's the established Embabel pattern.

Now, regarding your more important question about multi-turn conversation and resolution — that's a fundamental design challenge. Let me address that directly since it affects the architecture significantly:

Multi-Turn Resolution: How Embabel Handles It
Embabel provides 3 patterns for this problem:

Pattern 1: RepeatUntilAcceptable — Agent Self-Evaluates
From 

ReviseStoryUntilSatisfied.java
:

java
RepeatUntilAcceptableBuilder
    .returning(Story.class)
    .withMaxIterations(7)            // Safety cap
    .withScoreThreshold(.8)          // Score > 0.8 = done
    .repeating(context -> { ... })   // Generate attempt
    .withEvaluator(context -> { ...})// LLM scores it
    .build()
For your use case: The agent could loop — try a fix, ask the LLM "did we likely resolve it?", and repeat. But this doesn't involve the customer confirming.

Pattern 2: WaitFor.formSubmission() — Human-in-the-Loop
From 

Handoff.java
:

java
return WaitFor.formSubmission("Is your issue resolved?", ResolutionFeedback.class);
For your use case: After each troubleshooting step, the agent pauses and asks the customer "Did that fix it?" The customer's response drives the next action.

Pattern 3: @Condition + 

pre
/post — Conditional Branching
From 

Researcher.kt
:

kotlin
@Condition(name = REPORT_SATISFACTORY)
fun makesTheGrade(critique: Critique) = critique.accepted
@Condition(name = REPORT_UNSATISFACTORY)
fun rejected(critique: Critique) = !critique.accepted
Actions then use pre = [REPORT_UNSATISFACTORY] to only run when the condition is met — creating conditional loops.

What This Means for Your Chatbot
For a customer troubleshooting chatbot, you'd combine Pattern 2 + Pattern 3:

Customer: "My WiFi keeps dropping"
    → Supervisor classifies → BroadbandAgent
    → BroadbandAgent: "Try restarting your router. Did that fix it?"
    → WaitFor customer response
    → Customer: "No, still dropping"
    → @Condition(ISSUE_UNRESOLVED) → next troubleshooting step
    → BroadbandAgent: "Check for firmware updates. Did that help?"
    → WaitFor customer response
    → Customer: "Yes! It's working now"
    → @Condition(ISSUE_RESOLVED) → @AchievesGoal
The key insight: only the customer can confirm resolution, and WaitFor.formSubmission() is exactly how Embabel handles that pause-and-wait.

Would you like me to update the implementation plan to include this multi-turn conversation flow with the HITL loop pattern?

UNIT TEST PLANNER



Great question — let me find the existing test patterns in the Embabel examples:

Analyzed
Analyzed
Analyzed
Now let me also check for planner-specific tests — tests that verify the agent graph/plan structure rather than individual actions:

0 results
4 results
Now let me check if there are shell command tests and the x (execute) command for plan testing:

0 results
Read page

Good question. Embabel gives you two levels of testing for your agent workflow, and they serve different purposes. Let me break it down based on the actual test patterns in the codebase:

Level 1: Unit Test Individual Actions (No LLM Needed)
This is what the existing tests do. Using FakeOperationContext from embabel-agent-test, you test that each @Action method builds the right prompt with the right data — without calling any LLM.

From 

StarNewsFinderTest.java
:

java
var context = new FakeOperationContext();
context.expectResponse(new Writeup("Gonna be a good day"));  // Fake LLM response
starNewsFinder.writeup(starPerson, relevantNewsStories, horoscope, context.ai());
// Inspect what was sent to the LLM
var prompt = context.getLlmInvocations().getFirst().getMessages().getFirst().getContent();
assertTrue(prompt.contains(starPerson.getName()));     // Right data in prompt?
assertTrue(prompt.contains("Scorpio"));                 // Right sign?
var toolGroups = context.getLlmInvocations().getFirst().getInteraction().getToolGroups();
assertTrue(toolGroups.isEmpty());                       // No tools attached?
This tests "did I wire the prompt correctly?" — fast, deterministic, no API keys needed.

Level 2: Test the Planner via the Shell
To test whether the planner can find a valid path from 

UserInput
 → @AchievesGoal, you use the interactive shell. When you run the app and type:

x "My WiFi keeps dropping"
The framework will:

Discover all @Agent beans with their @Action methods
Build a graph of type transformations (input types → output types)
Plan a path from 

UserInput
 to the goal type (e.g., TroubleshootingResult)
Show the plan before executing it
If the planner can't find a path, it tells you immediately — for example, if there's a type gap between your actions (e.g., Action A outputs Foo but Action B needs Bar and nothing produces Bar).

What to Watch For
The planner works by matching types:

Each @Action declares what types it consumes (method parameters) and produces (return type)
The planner finds a path through these type transformations to reach the @AchievesGoal
So if your agent has:

java
@Action
RoutingDecision classifyIssue(UserInput input, Ai ai) { ... }
@Action
TroubleshootingResult routeToAgent(RoutingDecision decision, UserInput input, ...) { ... }
The planner sees: 

UserInput
 → classifyIssue → RoutingDecision → routeToAgent → TroubleshootingResult ✅

But if you had a gap:

java
@Action
RoutingDecision classifyIssue(UserInput input, Ai ai) { ... }
@Action
TroubleshootingResult routeToAgent(SomethingElse mystery, ...) { ... }  // ❌ Nothing produces SomethingElse!
The planner would fail to find a path and tell you.

Summary
What to test	How	LLM needed?
Prompts are correct	FakeOperationContext unit tests	❌ No
Tool groups are correct	FakeOperationContext unit tests	❌ No
Planner finds a valid path	Run shell → x "test input"	✅ Yes (to execute), but planner itself doesn't need LLM
End-to-end flow works	Run shell → x "real input"	✅ Yes
The FakeOperationContext approach from embabel-agent-test is the way to validate your agents work correctly without burning API calls. The shell run validates the planner graph is connected.


