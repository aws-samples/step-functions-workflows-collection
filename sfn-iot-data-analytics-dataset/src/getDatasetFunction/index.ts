import fetch from 'node-fetch';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
const crypto = require('crypto');

const client = new S3Client({ region: process.env.AWS_REGION });
const BUCKET = process.env.BUCKET;

export const handler = async (
  event: { Entries: any },
  context: any,
  callback: (arg0: null) => void,
) => {
  console.log(event);
  for (const record of event.Entries) {
    console.log(record.DataURI);
    const file = await fetch(record.DataURI);
    const body = await file.text();

    const objectKey = `data/${crypto.randomUUID()}.csv`;
    const putObjectCommand = new PutObjectCommand({
      Bucket: BUCKET,
      Key: objectKey,
      Body: body,
    });

    try {
      await client.send(putObjectCommand);
      return {
        Bucket: BUCKET,
        Key: objectKey,
      };
    } catch (error) {
      console.log(error);
    }
  }
};
