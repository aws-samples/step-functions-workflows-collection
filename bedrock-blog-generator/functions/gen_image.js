const {BedrockRuntime} = require('@aws-sdk/client-bedrock-runtime');
const {S3} = require('@aws-sdk/client-s3');

const br = new BedrockRuntime({region: 'us-west-2'});
const s3 = new S3();
const { S3_BUCKET } = process.env


/**
* @param key {string}
* @param file {buffer}
*/
const putS3File = async (key, file) => {
  const params = {
      Bucket: S3_BUCKET,
      Key: key,
      Body: file
  };
  return await s3.putObject(params)
}

exports.handler = async event => {
  console.log('EVENT:', event)
  const {intro, textLocation} = event

  const prompt = intro
  
  const params = {
    "modelId": "stability.stable-diffusion-xl-v0",
    "contentType": "application/json",
    "accept": "application/json",
    "body": "{\"text_prompts\":[{\"text\":\" " + prompt + "\"}],\"cfg_scale\":10,\"seed\":0,\"steps\":50}"
  }

  // Invoke the Bedrock model Stable Diffusion
  const res = await br.invokeModel(params)
  const {body} = res
  const output = JSON.parse(new TextDecoder().decode(body))
  const base64Img = output.artifacts[0].base64

  // Buffer and Put image to S3
  const buffer = Buffer.from(base64Img,'base64')
  await putS3File('GEN-CONTENT/image.png', buffer)

  return ({textLocation, imageLocation: 'GEN-CONTENT/image.png'})
};