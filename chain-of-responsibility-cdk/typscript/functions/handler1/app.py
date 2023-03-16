def lambda_handler(event, context):
    """Sample Lambda function which mocks the operation of dispensing $50 bills.

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

    if dispense > 50 :
        transaction_result ["dispense"] = str(dispense % 50) # what's left to dispense
        transaction_result ["50s"] = str(dispense // 50) # number of 50 dollar bills

    return transaction_result
