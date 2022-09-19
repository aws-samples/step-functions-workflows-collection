 
/*  
SPDX-FileCopyrightText: 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 
*/
const arr = process.env.ArrayToRoundRobin.split(',')

  exports.lambdaHandler = async(event) => {
console.log(arr)
    const executions = event.executions.Executions.length
    const index = executions % arr.length
    const item = arr[index]
    return item
  }