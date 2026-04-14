import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_claim_in_db(claim: str, api_key: str):
    api_key = api_key
    query = claim

    url = f"https://factchecktools.googleapis.com/v1alpha1/claims:search?query={query}&key={api_key}"

    try:
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Request failed with status code: {response.status_code}")
            logger.info(f'''Reason: {json.loads(response.text).get("error", {}).get("message", "Unknown error")}''')
            return None
    except Exception as e:
        return None

    data = response.json()
    output = {}

    if "claims" in data:
            for claim in data["claims"]:
                try:
                    output[f"{claim['text']}"] = {
                        "publisher": claim['claimReview'][0]['publisher'].get("name", "Unknown"),
                        "rating": claim['claimReview'][0]['textualRating'],
                        "source": claim['claimReview'][0]['url']
                }
                except Exception as e:
                    logger.error(f"[FactCheckDb]: {e}")
                    continue
    else:
        print("No fact checks found.")
    
    return output


# --- Testing ---
if __name__ == "__main__":
    claim = "<claim>"
    api_key = "<yourApiKey>"
    output = check_claim_in_db(api_key=api_key, claim=claim)
    print(json.dumps(output, indent=4))