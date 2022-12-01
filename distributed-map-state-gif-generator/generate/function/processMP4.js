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

	// Get signed URL for source object
	const params = {
		Bucket: process.env.SourceBucketName, 
		Key: originalMP4, 
		Expires
	}
	const url = s3.getSignedUrl('getObject', params)
	console.log('processMP4: ', { url, originalMP4, start, end })

	// Extract frames from MP4 (1 per second)
	console.log('Create GIF')
	const baseFilename = params.Key.split('.')[0]
	
	// Create GIF
	const gifName = `${baseFilename}-${start}.gif`
	// Generates gif in local tmp
	await execPromise(`${ffmpegPath} -loglevel error -ss ${start} -to ${end} -y -i "${url}" -vf "fps=10,scale=240:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 ${ffTmp}/${gifName}`)
	// Upload gif to local tmp
	// Generate frames
	if (process.env.GenerateFrames === 'true') {	
		console.log('Capturing frames')
	const dave =	await execPromise(`${ffmpegPath} -loglevel error -ss ${start} -to ${end} -i "${url}" -vf fps=1 ${ffTmp}/${baseFilename}-${start}-frame-%d.jpg`)
	}




	// Upload all generated files
	await uploadFiles(`${baseFilename}/`)

	// Cleanup temp files
	await tmpCleanup()

	 
}

module.exports = { processMP4 }