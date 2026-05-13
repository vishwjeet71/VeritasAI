from urllib.parse import urlparse

def classify_input(user_input):

    if user_input is None:
        raise TypeError("Input cannot be None")

    if not isinstance(user_input, str):
        raise TypeError("Input must be a string")

    user_input = user_input.strip()
    if not user_input:
        raise ValueError("Input is empty")

    try:
        parsed = urlparse(user_input)

        valid_scheme = parsed.scheme in ("http", "https")
        has_domain = bool(parsed.netloc)
        no_spaces_in_domain = " " not in parsed.netloc

        result = valid_scheme and has_domain and no_spaces_in_domain

        if parsed.scheme in ("http", "https") and not result:
            raise ValueError("invalid url")

    except ValueError:
        raise ValueError("invalid url")

    if result == True:
        return {
            "type": "url",
            "value": user_input
        }
    else:
        return {
            "type": "query",
            "value": user_input
        }