/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

'use strict'

// // Configure S3
const AWS = require('aws-sdk')
AWS.config.update({ region: process.env.AWS_REGION })
const s3 = new AWS.S3({ apiVersion: '2006-03-01' })

// Set paths for ffpmeg/ffprobe depending on local/Lambda usage
const ffmpegPath = (process.env.localTest) ? require('@ffmpeg-installer/ffmpeg').path : '/opt/bin/ffmpeg'
const ffTmp = (process.env.localTest) ? './tmp' : '/tmp'

const { uploadFiles } = require('./uploadToS3')
const { tmpCleanup } = require('./tmpCleanup')

const { exec } = require('child_process')

const Expires = 300

const execPromise = async (command) => {
	console.log(command)
	return new Promise((resolve, reject) => {
		const ls = exec(command, function (error, stdout, stderr) {
		  if (error) {
		    console.log('Error: ', error)
		    reject(error)
		  }
		  if (stdout) console.log('stdout: ', stdout)
		  if (stderr) console.log('stderr: ' ,stderr)
		})
		
		ls.on('exit', (code) => {
		  console.log('execPromise finished with code ', code)
		  resolve()
		})
	})
}

const processMP4 = async (event) => {
	// Get settings from the incoming event
	const originalMP4 = event.Key 
	const start =  event.start
	const end =  event.end

	// Input validation to prevent command injection
	if (!originalMP4 || typeof originalMP4 !== 'string') {
		throw new Error('Invalid Key parameter')
	}
	
	// Validate start and end parameters - must be positive numbers
	const startNum = parseFloat(start)
	const endNum = parseFloat(end)
	
	if (isNaN(startNum) || isNaN(endNum) || startNum < 0 || endNum < 0 || startNum >= endNum) {
		throw new Error('Invalid start or end time parameters')
	}
	
	// Sanitize the key to prevent path traversal
	const sanitizedKey = originalMP4.replace(/[^a-zA-Z0-9._-]/g, '_')
	
	// Get signed URL for source object
	const params = {
		Bucket: process.env.SourceBucketName, 
		Key: originalMP4, 
		Expires
	}
	const url = s3.getSignedUrl('getObject', params)
	console.log('processMP4: ', { url, originalMP4: sanitizedKey, start: startNum, end: endNum })

	// Extract frames from MP4 (1 per second)
	console.log('Create GIF')
	const baseFilename = sanitizedKey.split('.')[0]
	
	// Create GIF - use validated numeric parameters
	const gifName = `${baseFilename}-${startNum}.gif`
	// Generates gif in local tmp - parameters are now validated numbers
	await execPromise(`${ffmpegPath} -loglevel error -ss ${startNum} -to ${endNum} -y -i "${url}" -vf "fps=10,scale=240:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 ${ffTmp}/${gifName}`)
	// Upload gif to local tmp
	// Generate frames
	if (process.env.GenerateFrames === 'true') {	
		console.log('Capturing frames')
		await execPromise(`${ffmpegPath} -loglevel error -ss ${startNum} -to ${endNum} -i "${url}" -vf fps=1 ${ffTmp}/${baseFilename}-${startNum}-frame-%d.jpg`)
	}

	// Upload all generated files
	await uploadFiles(`${baseFilename}/`)

	// Cleanup temp files
	await tmpCleanup()
}

module.exports = { processMP4 }