// Mock event

const environmentVars = require('./env.json')
process.env.localTest = true

// Lambda handler
const { lambdaHandler } = require('./app')
const main = async () => {
  console.time('localTest')
  console.dir(await lambdaHandler({"anything":"here"}))
  console.timeEnd('localTest')
}
main().catch(error => console.error(error))