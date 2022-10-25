/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

'use strict'

const { processMP4 } = require('./processMP4')

// The Lambda handler
exports.lambdaHandler = async (event) => {
  console.log (JSON.stringify(event, null, 2))
  await processMP4 (event)
}