const {S3, S3Client, GetObjectCommand} = require('@aws-sdk/client-s3');
const {getSignedUrl} = require('@aws-sdk/s3-request-presigner');
const {marked} = require('marked');
const AdmZip = require('adm-zip');
const {randomUUID} = require('crypto');

const s3 = new S3();
const zip = new AdmZip();
const { S3_BUCKET } = process.env

/**
* @param key {string}
*/
const getS3File = async (key) => {
    const params = {
        Bucket: S3_BUCKET,
        Key: key
    };
    return await s3.getObject(params)
}

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
    const {textLocation, imageLocation} = event

    try {
        // Get Text and Image
        const textRes = await getS3File(textLocation)
        const textData = await textRes.Body.transformToString()
        const imageRes = await getS3File(imageLocation)
        const imageData = await imageRes.Body.transformToByteArray()

        // Stitch Gen Image to top of Blog
        const finalContent = `![Alt text](./image.png)\n\n ${textData}`
        const html = marked.parse(finalContent)

        // Create Zip file & Put S3
        zip.addFile('blog-final.md', Buffer.from(finalContent))
        zip.addFile('blog-final.html', Buffer.from(html))
        zip.addFile('image.png', imageData)

        const sendZip = await zip.toBufferPromise()
        const zipName = `GEN-CONTENT/${randomUUID()}.zip`
        await putS3File(zipName, sendZip)

        // Create Signed URL
        const client = new S3Client();
        const command = new GetObjectCommand({Bucket: S3_BUCKET, Key: zipName})
        const URL = await getSignedUrl(client, command, { expiresIn: 3600 })

        console.log('SUCCESS')
        return({signedURL: URL})

    }
    catch (err) {
        console.error(err)
    }
};