from urllib.parse import urlparse

def classify_input(user_input):
    try:
        result = urlparse(user_input)
        # A valid link should generally have both a scheme and a domain (netloc)
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


if __name__ =="__main__":
    url = str(input("Enter a URL: "))

    print(classify_input(url))