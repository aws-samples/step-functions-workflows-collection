// Mock event

const environmentVars = require('./env.json')
process.env.localTest = true

process.env = environmentVars

// Lambda handler
const { lambdaHandler } = require('./app')
const main = async () => {
  console.time('localTest')
  console.dir(await lambdaHandler({"executions":{"Executions":[1,2,3,4,5,6,7]}}))
  console.timeEnd('localTest')
}
main().catch(error => console.error(error))