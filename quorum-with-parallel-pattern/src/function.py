import random

# Sample function waits an arbitrary amount of time between 1 and 15 seconds before exiting (or failing).
# It could also arbitrarily fail, which is simulated if the value is 16
def handler(event, context):
    num = random.randint(1, 16)

    if (num>6):
        some_error = '\nException : Some error Occurred.\n'
        raise Exception(some_error)

    result = {
        "sleep_time": str(num)}

    return result
