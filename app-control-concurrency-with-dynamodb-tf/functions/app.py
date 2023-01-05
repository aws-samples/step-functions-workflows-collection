# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import time
import random


class RandomSimulatedFailure(Exception):
    pass

failure_threshold = 0.90
def lambda_handler(event, context):
    random_number = random.random()
    # Throw and exception if the random number is larger than the specified threshold
    if random_number > failure_threshold:
        raise RandomSimulatedFailure('Function failed because randomly generated number {} was larger than {}'.format(random_number,failure_threshold))
    else:
        time.sleep(15) 
        return 1