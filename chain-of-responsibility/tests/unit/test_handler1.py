from functions.handler1 import app


def test_handler1():
    dispense = 75
    input_payload = {"dispense": dispense}

    data = app.lambda_handler(input_payload, "")

    assert "dispense" in data
    assert "50s" in data

    assert data["50s"] == str("1")
    assert data["dispense"] == str("25")
