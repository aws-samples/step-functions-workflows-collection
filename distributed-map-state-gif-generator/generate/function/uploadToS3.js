/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

'use strict'

// // Configure S3
const AWS = require('aws-sdk')
AWS.config.update({ region: process.env.AWS_REGION })
const s3 = new AWS.S3({ apiVersion: '2006-03-01' })

const fs = require('fs')
const path = require('path')
const directory = (process.env.localTest) ? './tmp/' : '/tmp/'

// Uploads all of temp dir to 'folder' in S3.
const uploadFiles = async (folder) => {
	console.log('Starting uploadFiles')
	const files = await getFiles()
	console.log (`Files in ${directory}: `, files)

	// Upload files to S3
	const promises = files.map((file) => uploadToS3(file, folder))
	await Promise.allSettled(promises)
}



// Get all files in temp
const getFiles = async () => {
	return new Promise((resolve, reject) => {
		const files = fs.readdirSync(directory)

		// Filter list based on 'GenerateFrames' flag
		const filesToUpload = files.filter((file) => {
			const type = file.split('.')[1]
			if (type != 'jpg' && type != 'gif') return false
			return file
		})
		resolve(filesToUpload)
	})
}

// Upload to S3
const uploadToS3 = async (file, folder) => {
	const params = {
		Bucket: process.env.GifsBucketName,
		Key: `${folder}${file}`,
		Body: fs.readFileSync(path.join(directory,file)),
		ACL: 'public-read'
	}
	console.log('uploadToS3: ', params.Key)
	
	return s3.putObject(params).promise()
	
}

module.exports = { uploadToS3, uploadFiles }
