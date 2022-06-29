// Mock event

const environmentVars = require('./env.json')
process.env.localTest = true

// Lambda handler
const { lambdaHandler } = require('./app')
const main = async () => {
  console.time('localTest')
  console.dir(await lambdaHandler({"data":[1,2,4,5,6,7,8,6,3,4,5,6,3,2]}))
  console.timeEnd('localTest')
}
main().catch(error => console.error(error))