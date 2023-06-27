def do_lower(val: str):
    if val:
        return val.lower()
    return ""


def do_replace(val: str, find, replace_with):
    if val:
        return val.replace(find, replace_with)
    return ""


def add_prefix(val: str, prefix):
    if val:
        return f"{prefix}_{val}"
    return ""


def does_PK_name_not_exists(validation_key_name, item):
    """
    :param validation_key_name:
    :param item:
    :return: True/False
    """
    if validation_key_name not in item or item[validation_key_name].strip() == "":
        return True
    else:
        return False


def validate_and_transform_items(items: list, validation_key_name):
    bad_list = []
    clean_list = []
    for item in items:
        if does_PK_name_not_exists(validation_key_name=validation_key_name, item=item):
            bad_list.append(item)
        else:
            santized_item = transform_data(item)
            clean_list.append(santized_item)

    return clean_list, bad_list


def lower_and_replace(val: str, find, replace_with):
    if val:
        return do_replace(do_lower(val), find, replace_with)
    return ""


def transform_data(item: dict):
    santized_item: dict = {}
    char_find = " "
    char_replace_with = "_"

    for key in item.keys():
        santized_item[lower_and_replace(key, char_find, char_replace_with)] = item[key]

    if "dol_vehicle_id" in santized_item:
        santized_item["dol_vehicle_id"] = add_prefix(
            santized_item["dol_vehicle_id"], prefix="A"
        )
    else:
        santized_item["dol_vehicle_id"] = ""
    return santized_item
