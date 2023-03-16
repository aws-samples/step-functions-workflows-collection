def lambda_handler(event, context):
    """Sample Lambda function which mocks the operation of dispensing $1 bills.

    For demonstration purposes, this Lambda function does not actually perform any
    actual transactions. It simply returns a mocked result.

    Parameters
    ----------
    event: dict, required
        Input event to the Lambda function

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
        dict: Object containing details of the dispensed money
    """

    transaction_result = event

    # Get the amount to dispense
    dispense = int(transaction_result["dispense"])

    if dispense >= 1 :
        transaction_result ["dispense"] = str(dispense % 1) # what's left to dispense
        transaction_result ["1s"] = str(dispense // 1) # number of 1 dollar bills

    return transaction_result
