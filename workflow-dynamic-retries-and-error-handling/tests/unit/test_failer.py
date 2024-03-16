import pytest
from functions.rate_failer import app


def test_rate_failer_always_succeed():
    input_payload = {"failureRate": 0}

    data = app.lambda_handler(input_payload, "")

    assert "randomDraw" in data


def test_rate_failer_always_fail():
    input_payload = {"failureRate": 1}

    with pytest.raises(Exception) as e:
        data = app.lambda_handler(input_payload, "")
