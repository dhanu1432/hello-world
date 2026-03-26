does embabel offer any test utility for testing goap plans for unit testing or to verify path for goals
Fast
View as codemap
Yes, Embabel provides comprehensive test utilities for testing GOAP plans, including unit testing support and path validation for goals.

Key Test Utilities for GOAP Plans
1. GoapPlannerTest - Comprehensive Unit Testing
The GoapPlannerTest class provides extensive test scenarios for GOAP planning GoapPlannerTest.kt:36-240 :

@Test  
fun `single plan`() {  
    val planner = AStarGoapPlanner(EmptyWorldStateDeterminer)  
    val plan = planner.planToGoal(actions, getAwayWithMurderGoal)  
    assertTrue(plan != null)  
    assertEquals(bestPlanActions, plan!!.actions.map { it.name })  
}
This test class includes:

Single plan validation
Multiple plan discovery
Best plan selection for any goal
Path finding from unknown states
Scalability testing with 300+ actions
2. GoapPathToCompletionValidator - Goal Path Validation
The GoapPathToCompletionValidator validates that agent definitions have achievable paths to goals GoapPathToCompletionValidator.kt:38-52 :

class GoapPathToCompletionValidator : PathToCompletionAgentValidator {  
    override fun validate(agentScope: AgentScope): ValidationResult {  
        // Creates initial world state from agent actions  
        // Converts actions to GOAP format (removing hasRun_ conditions)  
        // Tests each goal for achievable path  
        // Returns detailed validation errors  
    }  
}
3. PlanTest - Plan Metrics Testing
The PlanTest class verifies plan calculations and completion status PlanTest.kt:39-120 :

@Test  
fun `test plan cost calculation`() {  
    val plan = Plan(actions, goal)  
    assertEquals(7.0, plan.cost(mockk()))  
}
Implementation Examples
Testing Plan Creation and Validation
@Test  
fun `test goal achievement path`() {  
    // Create actions with preconditions and effects  
    val cookDrugs = ConditionAction(  
        name = "Cook drugs",  
        preconditions = emptyMap(),  
        effects = mapOf("hasDrugs" to ConditionDetermination(true)),  
        cost = { 1.20 }  
    )  
      
    val sellDrugs = ConditionAction(  
        name = "Sell drugs",   
        preconditions = mapOf("hasDrugs" to ConditionDetermination(true)),  
        effects = mapOf("hasMoney" to ConditionDetermination(true)),  
        cost = { 1.20 }  
    )  
      
    // Test plan creation  
    val planner = AStarGoapPlanner(EmptyWorldStateDeterminer)  
    val plan = planner.planToGoal(setOf(cookDrugs, sellDrugs), hasMoneyGoal)  
      
    assertNotNull(plan)  
    assertEquals(listOf("Cook drugs", "Sell drugs"), plan.actions.map { it.name })  
}
GoapPlannerTest.kt:118-126

Using the Validator in Unit Tests
@Test  
fun `validate agent has achievable goals`() {  
    val validator = GoapPathToCompletionValidator()  
    val result = validator.validate(myAgentScope)  
      
    assertTrue(result.isValid,   
        "Agent should have valid paths: ${result.errors.joinToString()}")  
}
GoapPathToCompletionValidator.kt:180-217

Advanced Testing Features
World State Determination
The framework supports testing with different world states GoapPlannerTest.kt:156-175 :

val touchyWorldStateDeterminer = object : WorldStateDeterminer {  
    override fun determineWorldState(): ConditionWorldState {  
        return ConditionWorldState(  
            state = mapOf(  
                "hasMoney" to ConditionDetermination(true),  
                "enemyDead" to ConditionDetermination.UNKNOWN  
            )  
        )  
    }  
}
Action Leakage Testing
The AutonomyActionLeakageTest ensures actions don't leak between different goals AutonomyActionLeakageTest.kt:56-90 .

Notes
The AStarGoapPlanner is the default GOAP implementation used in tests
Tests can be run with custom WorldStateDeterminer implementations
The validator automatically handles hasRun_ condition filtering
Plan testing includes cost, value, and net value calculations
All test utilities are designed for both unit and integration testing scenarios
Wiki pages you might want to explore:

Testing (embabel/embabel-agent)
Wiki pages you might want to explore:

Agent Platform and Execution Modes (embabel/embabel-agent)
