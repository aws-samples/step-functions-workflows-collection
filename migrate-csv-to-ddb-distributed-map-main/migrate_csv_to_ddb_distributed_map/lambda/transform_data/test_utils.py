import os
import utils


def test_does_PK_name_not_exists():
    validation_key_name = "vehicle_id"
    item = {"hello": "world"}
    assert utils.does_PK_name_not_exists(validation_key_name, item) is True
    item = {validation_key_name: "xxxx"}

    assert utils.does_PK_name_not_exists(validation_key_name, item) is False


def test_add_prefix():
    value_to_add_prefix = "abc"
    prefix = "A"
    assert (
        utils.add_prefix(value_to_add_prefix, prefix)
        == f"{prefix}_{value_to_add_prefix}"
    )
    assert utils.add_prefix(None, prefix) is ""


def test_do_replace():
    value_to_replace = "hello world"
    replace_with = "_"
    replace_this = " "

    assert (
        utils.do_replace(value_to_replace, replace_this, replace_with) == "hello_world"
    )
    assert utils.do_replace(None, replace_this, replace_with) == ""


def test_do_lower():
    value_to_lower = "Hello World"
    assert utils.do_lower(value_to_lower) == "hello world"
    assert utils.do_lower(None) == ""


def test_lower_and_replace():
    value_to_lower_replace = "hello World Hi"
    assert utils.lower_and_replace(value_to_lower_replace, " ", "_") == "hello_world_hi"


def test_transform_data():
    item_to_transform = {"DOL Vehicle Id": "asdasd", "VIN": "sample VIN number"}

    assert utils.transform_data(item_to_transform) == {
        "dol_vehicle_id": "A_asdasd",
        "vin": "sample VIN number",
    }

    item_to_transform = {"VIN": "sample VIN number"}

    assert utils.transform_data(item_to_transform) == {
        "dol_vehicle_id": "",
        "vin": "sample VIN number",
    }


def test_validate_and_transform_items():
    KEY_VALIDATION_NAME = "DOL Vehicle ID"
    items_to_validate_transform = [
        {"DOL Vehicle ID": "asdasd", "VIN": "sample VIN number"},
        {"VIN": "sample VIN number"},
    ]

    clean_list, bad_list = utils.validate_and_transform_items(
        items=items_to_validate_transform, validation_key_name=KEY_VALIDATION_NAME
    )
    print(f"CLEAN : {len(clean_list)}, BAD : {len(bad_list)}")
    assert len(clean_list) == 1
    assert len(bad_list) == 1
