const {BedrockRuntime} = require('@aws-sdk/client-bedrock-runtime');
const {S3} = require('@aws-sdk/client-s3');

const br = new BedrockRuntime({region: 'us-west-2'});
const s3 = new S3();
const { S3_BUCKET } = process.env

const example = 'Write a blog on the benefits of saving early in life.'


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

exports.handler = async (event) => {
  console.log('EVENT:', event)
  const {input} = event
  // Concat Input with template prompt
  const prompt = `${input} Include a title, an introduction section, sub sections and a conclusion section, and output in Markdown. Respond in <response> XML tag.`
  
  const params = {
      "modelId": "anthropic.claude-v2",
      "contentType": "application/json",
      "accept": "*/*",
      "body": "{\"prompt\":\"Human: \\n\\nHuman: "+prompt+"\\n\\n\\nAssistant:\",\"max_tokens_to_sample\":600,\"temperature\":1,\"top_k\":250,\"top_p\":0.999,\"stop_sequences\":[\"\\n\\nHuman:\"],\"anthropic_version\":\"bedrock-2023-05-31\"}"
    }
  
  // Invoke the Bedrock model Claude-v2
  const res = await br.invokeModel(params)
  const {body} = res
  const output = JSON.parse(new TextDecoder().decode(body))
  const text = output.completion

  // Remove XML tag from output
  const mdText = text.split('<response>\n\n')[1].split('\n\n</response>')[0]
  console.log(mdText)

  // Put Markdown file to S3
  await putS3File('GEN-CONTENT/blog-text.md', mdText)

  var getIntro;
  // Check for intro section to grab sentence for GenImage
  if (mdText.includes('## Introduction')) {
    console.log('GRAB INTRO SENTENCE')
    getIntro = mdText.split('## Introduction\n\n')[1].split('\n\n##')[0]
  }
  else {
    getIntro = mdText.split('\n\n')[1]
  }

  return({intro: getIntro, textLocation: 'GEN-CONTENT/blog-text.md'})
};