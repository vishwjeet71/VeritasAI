from urllib.parse import urlparse

def classify_input(user_input):
    try:
        result = urlparse(user_input)
        result = all([result.scheme, result.netloc])
    except ValueError:
        result = False
    
    if result == True:
        return {
            "type":"url",
            "value":user_input
        }
    else:
        return {
            "type":"query",
            "value":user_input
        }