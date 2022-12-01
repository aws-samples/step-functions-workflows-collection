/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

"use strict"

// Set paths for ffpmeg/ffprobe depending on local/Lambda usage
const ffmpegPath = process.env.localTest ? require("@ffmpeg-installer/ffmpeg").path : "/opt/bin/ffmpeg"
const ffprobePath = process.env.localTest ? require("@ffprobe-installer/ffprobe").path : "/opt/bin/ffprobe"

// Configure ffmpeg
const ffmpeg = require("fluent-ffmpeg")
ffmpeg.setFfmpegPath(ffmpegPath)
ffmpeg.setFfprobePath(ffprobePath)

// Configure S3
const AWS = require("aws-sdk");
AWS.config.update({ region: process.env.AWS_REGION })
const s3 = new AWS.S3({ apiVersion: "2006-03-01" })
const fs = require("fs")

const IMG_WIDTH = 240
const IMG_HEIGHT = 135

const ffProbe = async (source) => {
  console.log("ffProbe: ", source)
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(source, function (err, metadata) {
      if (err) return reject(err)
      resolve(metadata)
    })
  })
}

const ffCreateSnippets = async (source, start, snippetSize, key) => {
  console.log("ffCreateSnippets: ", { source, start, snippetSize, key } )

  return new Promise((resolve, reject) => {
    // Get start/end for snippets
    const end = start + snippetSize - 1
    const startFormatted = new Date(start * 1000).toISOString().substr(11, 8)
    const endFormatted = new Date(end * 1000).toISOString().substr(11, 8)

    // Determine output location - use /tmp when deployed
    const outputPath = process.env.localTest ? "./tmp/" : "/tmp/"
    const outputKey = `${key.split(".")[0]}-${start}.mp4`
    const outputFile = `${outputPath}${outputKey}`
    console.log("Processing: ", {
      start,
      end,
      startFormatted,
      endFormatted,
      outputFile,
    })

    // Create snippet using ffpmeg
    ffmpeg(source)
      .noAudio()
      .size(`${IMG_WIDTH}x${IMG_HEIGHT}`)
      .setStartTime(startFormatted)
      .setDuration(snippetSize - 1)
      .output(outputFile)
      .on("end", async (err) => {
        if (err) reject(err)
        // Read file from local tmp buffer
        const buffer = fs.readFileSync(outputFile)

        // Upload to target S3 bucket
        const params = {
          Body: buffer,
          Bucket: process.env.SnippetsBucketName,
          Key: outputKey,
        }
        await s3.putObject(params).promise()
        console.log('S3 write complete for: ', outputKey)

        resolve("done")
      })
      .on("error", function (err) {
        console.error('FFMPEG error: ', err)
        reject(err)
      })
      .run()
  })
}

module.exports = { ffProbe, ffCreateSnippets }
