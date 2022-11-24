from functions.handler2 import app


def test_handler2():
    dispense = 75
    input_payload = {"dispense": dispense}

    data = app.lambda_handler(input_payload, "")

    assert "dispense" in data
    assert "20s" in data

    assert data["20s"] == str("3")
    assert data["dispense"] == str("15")
