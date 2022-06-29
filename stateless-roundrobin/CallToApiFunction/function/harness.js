// Mock event

const environmentVars = require('./env.json')
process.env.localTest = true

process.env = environmentVars
// Lambda handler
const { lambdaHandler } = require('./app')
const main = async () => {
  console.time('localTest')
  console.dir(await lambdaHandler({"assignee":1}))
  console.timeEnd('localTest')
}
main().catch(error => console.error(error))ls -l