Since you are using Embabel + a custom MongoDB blackboard, the behavior you described (actions repeating) almost always happens because the planner cannot see that the world state has changed.

Below is the practical architecture pattern used in production Embabel systems to prevent repeated actions and to debug planners.

I’ll explain 3 things:
	1.	Correct Mongo Blackboard design
	2.	How the planner decides to run actions
	3.	How to debug why an action is chosen

⸻

1. Correct Mongo Blackboard Design (Most Important)

Embabel’s planner reasons using objects on the blackboard.

The planner does NOT care whether the action ran — it cares about state.

Meaning:

Action runs → produces new state → planner sees goal closer → action not needed again

So your Mongo blackboard must persist three categories of information.

⸻

A. Domain Objects (World State)

These represent facts about the world.

Example:

CustomerAccount
ModemStatus
WifiDiagnosis
OutageStatus

Mongo collection example:

blackboard_objects

Example document:

{
  "sessionId": "abc123",
  "type": "ModemStatus",
  "data": {
      "online": true,
      "signalStrength": -55
  }
}

Planner reasoning example:

Goal: modemOnline = true

If ModemStatus.online = true
→ goal satisfied
→ action not executed again

If this object disappears or is not restored, the planner will rerun the action.

⸻

B. Action Execution History

Embabel internally tracks:

hasRun(action)

You should persist this.

Example collection:

blackboard_actions

Example document:

{
  "sessionId": "abc123",
  "action": "checkModem",
  "status": "completed",
  "timestamp": 1712000023
}

When restoring session:

markActionAsExecuted(checkModem)

If you don’t restore this, Embabel thinks:

action never executed


⸻

C. Planner State (Optional but Recommended)

For long workflows you should persist:

currentGoal
plan
actionQueue

Example collection:

agent_sessions

Example:

{
  "sessionId": "abc123",
  "goal": "FixInternetConnection",
  "currentStep": "CheckModem"
}

This prevents planner resets.

⸻

2. How the Embabel Planner Actually Decides Actions

Understanding this helps eliminate repeats.

Embabel uses Goal-Oriented Action Planning (GOAP).

Planning works like this:

Goal
↓
Find actions that can achieve goal
↓
Check preconditions
↓
Check world state
↓
Choose best action

Example:

Goal:

InternetWorking

Planner graph:

InternetWorking
   ↑
RestartRouter
   ↑
CheckModem

Execution:

1 CheckModem
2 RestartRouter
3 VerifyConnection

After each action:

re-evaluate state

If the world state doesn’t change, the planner thinks:

goal still unmet
→ run action again


⸻

3. Correct Action Design Pattern

Your actions must produce state objects.

Bad design:

@Action
public void checkModem(CustomerAccount account)

Planner sees no state change.

⸻

Correct design:

@Action
public ModemStatus checkModem(CustomerAccount account)

Return object becomes world state.

Example:

ModemStatus{online=true}

Now planner sees:

modem already checked


⸻

4. Avoid Stateless Actions

This is a common mistake.

Bad:

checkOutage()
checkOutage()
checkOutage()

Planner repeats.

Correct:

OutageStatus

Once present, planner skips action.

⸻

5. Best Mongo Blackboard Data Model

Recommended collections:

agent_sessions
blackboard_objects
blackboard_actions
agent_events

Example structure:

agent_sessions
   sessionId
   goal
   status

blackboard_objects
   sessionId
   objectType
   jsonData

blackboard_actions
   sessionId
   actionName
   executionState

agent_events
   logs

This allows full replay and debugging.

⸻

6. How to Debug Planner Decisions

Embabel planners are explainable.

You should log:

goal
world state
candidate actions
chosen action
reason

Example debug log:

Goal: InternetWorking

World State:
- CustomerAccount
- ModemStatus(online=true)

Candidate Actions:
- RestartRouter
- CheckOutage

Chosen:
CheckOutage

Reason:
OutageStatus missing

This instantly tells you why an action runs.

⸻

7. Add Planner Visualization (Extremely Useful)

In production systems we log the plan graph.

Example:

Goal: InternetWorking

Plan Graph:

CheckModem
   ↓
RestartRouter
   ↓
VerifyConnection

After each action:

replan

If graph does not change → bug in world state.

⸻

8. Debug Trick: Print Blackboard State

Before planner runs:

logBlackboard()

Example output:

Blackboard:

CustomerAccount
ModemStatus(online=true)
WifiDiagnosis(signal=-55)

If objects disappear → persistence bug.

⸻

9. Prevent Infinite Loops Automatically

You can configure a max action repetition limit.

Example:

maxActionExecutions = 1

Or:

maxIterations = 20

This prevents runaway loops.

⸻

10. Best Architecture for Large Agent Systems

For systems like yours (troubleshooting agents):

Use this pattern:

Supervisor Agent
      ↓
Issue Agent
      ↓
Actions

Example:

Supervisor
   ↓
WifiAgent
   ↓
CheckSignal
RestartRouter
CheckInterference

Each agent gets its own blackboard namespace.

⸻

11. Real Production Tip

Never store raw LLM outputs as state.

Instead convert to domain objects:

Bad:

"modem seems offline"

Good:

ModemStatus{online=false}

This makes the planner deterministic.

⸻

12. Why Embabel Feels Weird at First

Because it is state-driven, not workflow-driven.

Normal code:

step1
step2
step3

Embabel:

state1 → action
state2 → action
state3 → done

Planner figures out order.

⸻

If you’re interested, I can also show you something very useful:

Embabel Production Debug Tool

A small component that shows:

Goal
Plan
Actions executed
Blackboard state

in a web UI similar to LangSmith or LangGraph Studio.

It makes debugging agents 10x easier.
