async def get_value_default(key):
    """
    Get settings default value.
    
    :param key: "enabled", "interval", "quantum".
    :return: Integer.
    """
    if key == "enabled":
        result = 1
    elif key == "quantum":
        result = 4
    elif key == "interval":
        result = 30
    return result
