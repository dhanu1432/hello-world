Chain: Linear pipelines where each step transforms the previous output
Branch: Decision points that produce different types based on logic
Aggregate: Gather multiple perspectives or parallel computations
BiAggregate: Aggregation requiring two different input types
Split: Fan-out from one item to many of the same type
Repeat: Iterative refinement until a quality threshold is met
----------------
Action Types Used by Flow Patterns
Action Type Mapping

Pattern	    Primary Action Type	        Secondary Types	  Source File
Chain	      TransformationAction<I, O>	N/A	              TransformationAction.kt
Branch	    BranchingAction<I, O1, O2>	N/A	              BranchingAction.kt
Aggregate	  TransformationAction<A, B> (transforms)	TransformationAction<List<B>, C> (merge), ComputedBooleanCondition (completion)	TransformationAction.kt
BiAggregate	TransformationAction<Aggregation, B> (transforms)	TransformationAction<List<B>, C> (merge), ComputedBooleanCondition (completion)	TransformationAction.kt
Split	      ConsumerAction<A>	N/A	ConsumerAction.kt
Repeat	Varies (from what())	TransformationAction<C, C> (completion), ComputedBooleanCondition (until)	TransformationAction.kt

Key Action Classes:

TransformationAction<I, O>: Generic transformation from input type I to output type O. Executes a Transformation<I, O> block.
BranchingAction<I, O1, O2>: Declares two possible output types. Executes a block returning Branch<O1, O2>.
ConsumerAction<A>: Consumes input without producing a named output binding. Used by split to add multiple objects to the blackboard.
SupplierAction<O>: Produces output without requiring input. Used for initial values in repeatableAggregate.
ComputedBooleanCondition: A Condition that evaluates a predicate against the current OperationContext. Used for completion detection and loop termination.
