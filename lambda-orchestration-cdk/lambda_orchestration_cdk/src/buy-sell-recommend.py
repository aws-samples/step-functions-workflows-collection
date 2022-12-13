""" 
Sample Lambda function which mocks making the decision to buy or sell a stock
based on price.  For demonstration purposes, this function simply returns a 'buy' or 'sell'
string depending on the supplied price.

 """


def handler(event, context):

    # determine if we should buy or sell based on price
    _price = int(event["stock_price"])

    return "sell" if _price > 50 else "buy"
