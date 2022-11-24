from functions.handler4 import app


def test_handler4():
    dispense = 75
    input_payload = {"dispense": dispense}

    data = app.lambda_handler(input_payload, "")

    assert "dispense" in data
    assert "1s" in data

    assert data["1s"] == str("75")
    assert data["dispense"] == str("0")
