def valid_sponsor_channel(value):
    normalized = normalize_sponsor_channel(value)
    if not normalized:
        return False
    if normalized.startswith("+"):
        return False
    if normalized.lstrip("-").isdigit():
        return False
    return True


def normalize_sponsor_channel(value):
    value = value.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    return value.lstrip("@")
