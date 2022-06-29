# The "Query Athena” pattern


How to use an AWS Step Functions state machine to query Athena and get the results by leveraging Step Function native integration with Amazon Athena.

This sample project demonstrates how to use an AWS Step Functions state machine to query Athena and get the results.

This pattern is leveraging the native integration between these 2 services which means only JSON-based, structured language is used to define the implementation.

With Amazon Athena you can get up to 1000 results per invocation of the GetQueryResults method and this is the reason why the Step Function has a loop to get more results.

![query athena](http://serverlessland.com/assets/images/workflows/query-athena.png)
