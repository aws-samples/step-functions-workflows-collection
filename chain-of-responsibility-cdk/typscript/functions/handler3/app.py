def lambda_handler(event, context):
    """Sample Lambda function which mocks the operation of dispensing $10 bills.

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

    if dispense > 10 :
        transaction_result ["dispense"] = str(dispense % 10) # what's left to dispense
        transaction_result ["10s"] = str(dispense // 10) # number of 10 dollar bills

    return transaction_result
