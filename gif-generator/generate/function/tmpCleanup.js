/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

const fs = require('fs')
const path = require('path')
const directory = (process.env.LocalTest) ? './tmp' : '/tmp/'

// Deletes all files in a directory
const tmpCleanup = async () => {
	console.log('Starting tmpCleanup')
	fs.readdir(directory, (err, files) => {
		return new Promise((resolve, reject) => {
			if (err) reject(err)
			console.log('Deleting: ', files)				

			for (const file of files) {
				const fullPath = path.join(directory, file)
				fs.unlink(fullPath, err => {
					if (err) reject (err)
				})
			}
			resolve()
		})
	})
}

module.exports = { tmpCleanup }
