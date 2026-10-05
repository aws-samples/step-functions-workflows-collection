/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

'use strict'

// Configure S3
const { S3Client, GetObjectCommand } = require('@aws-sdk/client-s3')
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner')
const s3 = new S3Client({ region: process.env.AWS_REGION })

const { ffProbe } = require('./ffmpeg-promisify')
const { writeBatch } = require ('./eventbridge.js')

const createSnippets = async (record) => {
	// Get signed URL for source object
	const params = {
		Bucket: record.s3.bucket.name, 
		Key: record.s3.object.key
	}
	const url = await getSignedUrl(s3, new GetObjectCommand(params), { expiresIn: 300 })

	// Get length of source video
	const metadata = await ffProbe(url)
	const length = metadata.format.duration
	console.log('Length (seconds): ', length)

	// Build data array for EventBridge events
	const items = []
	const snippetSize = parseInt(process.env.SnippetSize)

	for (let start = 0; start < length; start += snippetSize) {
		items.push({
			Key: record.s3.object.key,
			start,
			end: (start + snippetSize - 1),
			length,
			tsCreated: Date.now()
		})
	}
	// Send events to EventBridge
	await writeBatch(items)
}

module.exports = { createSnippets }
