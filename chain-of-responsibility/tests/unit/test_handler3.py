from functions.handler3 import app


def test_handler3():
    dispense = 75
    input_payload = {"dispense": dispense}

    data = app.lambda_handler(input_payload, "")

    assert "dispense" in data
    assert "10s" in data

    assert data["10s"] == str("7")
    assert data["dispense"] == str("5")
