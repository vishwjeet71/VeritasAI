import requests, logging, json 
import numpy as np, os
from backend.evidence_extractor import Transformer
from dotenv import load_dotenv
load_dotenv()

_api_key =  os.getenv("FactCheckDbApi")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def relevantResults(fx):

    def wrapper(*args, **kwargs):
        check_claim_in_db_output = fx(*args, **kwargs)

        if check_claim_in_db_output is None:
            return None

        tf = kwargs["embedding_obj"]

        try: 
            root_claim = kwargs["claim"]
            result_claims = list(check_claim_in_db_output.keys())

            root_emb = tf.get_embeddings(root_claim)
            result_embs = tf.get_embeddings(result_claims)

            dot_product = np.dot(result_embs, root_emb)

            norm_root = np.linalg.norm(root_emb)
            norm_results = np.linalg.norm(result_embs, axis=1)

            scores = dot_product / (norm_results * norm_root)
            indices = np.where(scores > 0.80)[0]

            relevantResultsDict = {}

            for index in indices:
                relevantResultsDict[result_claims[index]] = check_claim_in_db_output[result_claims[index]]

            if relevantResultsDict:
                return relevantResultsDict
            else:
                return None
        
        except Exception as e:
            logger.error(f"[relevantResults]: {e}")
            return None
    
    return wrapper


@relevantResults
def check_claim_in_db(claim: str, searchQuerys: list[str], embedding_obj: object, api_key: str = _api_key):
    api_key = api_key
    searchQuerys = searchQuerys

    if not isinstance(searchQuerys, list):
        logger.error("[check_claim_in_db] Invalid input: searchQuerys must be a list")
        return None
    
    if len(searchQuerys) == 0:
        logger.info("[check_claim_in_db] get null input")
        return None
    

    output = {}
    responses = []

    for query in searchQuerys:

        url = f"https://factchecktools.googleapis.com/v1alpha1/claims:search?query={query}&key={api_key}"

        try:
            response = requests.get(url)
            if response.status_code != 200:
                logger.error(f"Request failed for query: {query} with status code: {response.status_code}")
                logger.info(f'''Reason: {json.loads(response.text).get("error", {}).get("message", "Unknown error")}''')
                responses.append(None)
                continue
            
            responses.append(response.json())
            logger.info(f"For '{query}' we found {len(response.json()['claims'])} claims")
        except Exception as e:
            responses.append(None)
        
    for index, data in enumerate(responses):

        if data is None:
            logger.warning(f"No data found for query: {searchQuerys[index]}")
            continue

        if "claims" in data:
                for claim in data["claims"]:
                    try:
                        if claim['text'] in output:
                            logger.warning(f"Duplicate claim found: {claim['text']}")
                            continue

                        output[f"{claim['text']}"] = {
                            "publisher": claim['claimReview'][0]['publisher'].get("name", "Unknown"),
                            "rating": claim['claimReview'][0]['textualRating'],
                            "source": claim['claimReview'][0]['url']
                    }
                    except Exception as e:
                        logger.error(f"[FactCheckDb]: {e}")
                        continue
        else:
            logger.warning(f"response does not contain claims for query: {searchQuerys[index]}")

    if output:
        return output
    else:
        return None