/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

'use strict'

const { processMP4 } = require('./processMP4')

// The Lambda handler
exports.lambdaHandler = async (event) => {

  const file = await processMP4 (event)
  return file
}