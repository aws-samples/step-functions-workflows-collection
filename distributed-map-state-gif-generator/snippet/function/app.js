/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

'use strict'

//const { createSnippets } = require('./snippet')
const { ffProbe } = require('./ffmpeg-promisify')
const AWS = require('aws-sdk')
AWS.config.update({ region: process.env.AWS_REGION })
const s3 = new AWS.S3({ apiVersion: '2006-03-01' })

// The Lambda handler
exports.lambdaHandler = async (event) => {

	const params = {
		Bucket: event.bucket, 
		Key: event.key, 
		Expires: 300
	}

  	const url = s3.getSignedUrl('getObject', params)

	// Get length of source video
	const metadata = await ffProbe(url)
	const length = metadata.format.duration
	console.log('Length (seconds): ', length)

	// Build data array for EventBridge events
	const items = []
	const snippetSize = parseInt(process.env.SnippetSize)

	for (let start = 0; start < length; start += snippetSize) {
		items.push({
			Key: event.key,
			start,
			end: (start + snippetSize - 1),
			length,
			tsCreated: Date.now()
		})
	}
	// Send events to EventBridge
	//await writeBatch(items)
	return items
  
  
}