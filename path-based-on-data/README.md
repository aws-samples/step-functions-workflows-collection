# The “Path based on Data” pattern
A Choice state adds branching logic to a state machine. You can think of this like a switch statement common in many programming languages. A Choice state has an array of rules. Each rule contains two things: an expression that evaluates some boolean expression, and a reference to the next state to transition to if this rule matches successfully. All of the rules are evaluated in order and the first rule to match successfully causes the state machine to transition to the next state defined by the rule.

In our example workflow, we want to move on to `NEXT_STATE_ONE` if the input payload `$.type` is set to `Private`. Move to `NEXT_STATE_TWO` if the `$.value` is between 20 and 30. If neither of these criteria are met then the execution will fall back to the `DEFAULT_STATE`.

![Path based on data](https://serverlessland.com/assets/images/workflows/branch-on-data.png)