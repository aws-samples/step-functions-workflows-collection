import re

def lambda_handler(event, context):
    for attr in event.keys():
        # regular expression to find attr that ends in 'Failure'
        if re.search(r'Failure$', attr):
            #remove 'Failure' from the end of the attribute name
            failed_task = attr.replace('Failure', '')
            print(f'found the failed_task: {failed_task}')
            print(attr, event[attr])
            # further error reporting or handling logic goes here

    return failed_task
