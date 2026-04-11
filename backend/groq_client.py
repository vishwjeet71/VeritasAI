from prompts import REPHRASE_AND_SCORE_PROMPT, SEARCH_QUERY_PROMPT
import logging, groq, json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rephrase_and_score(
        candidates: list[str],
        client,
        model_name = "llama-3.3-70b-versatile"
        ) -> list[dict]:

    numbered = "\n".join(
        [f"{i+1}. {sent}" for i, sent in enumerate(candidates)]
    )
    prompt = REPHRASE_AND_SCORE_PROMPT.replace("{candidates}", numbered)
    
    try:
        response = client.chat.completions.create(
            model= model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
    except groq.AuthenticationError as e:
        logger.error(f"[rephraseAndScore] Authentication error: {e}")
        return []
    except Exception as e:
        logger.error(f"[rephraseAndScore] unexpected Error during factExtraction processing: {e}")
        return []
        
    raw = response.choices[0].message.content.strip()

    try:
        results = json.loads(raw)
        valid = [r for r in results if r["claim"] is not None]
        return sorted(valid, key=lambda x: x["score"], reverse=True)[:5]

    except json.JSONDecodeError as e:
        logger.error(f"[rephraseAndScore] JSON decoding error: {e}")
        return []
    
    except Exception as e:
        logger.error(f"[rephraseAndScore] Error: {e}")
        return []


def generate_search_queries(
        claims: list[str],
        client,
        model_name: str = "llama-3.3-70b-versatile"
        ) -> list[dict]:
    
    numbered = "\n".join(
        [f"{i+1}. {claim}" for i, claim in enumerate(claims)]
    )
    prompt = SEARCH_QUERY_PROMPT.replace("{claims}", numbered)

    response = client.chat.completions.create(
        model= model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()

    try:
        queries = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"[queryGeneration] JSON decoding error: {e}")
        return []

    return queries

def generate_verdict(
        claim: str,
        evidence_chunks: list[str], 
        source_urls: list[str],
        model_name: str = "llama-3.3-70b-versatile"
)-> dict:
    pass

# --- Testing ---
if __name__ == "__main__":

    client = groq.Groq(api_key= "<yourApiKey>")

    candidates = [] # output of extract_candidate_sentences
    topClaims = rephrase_and_score(candidates=candidates, client=client)
    print(json.dumps(topClaims, indent=4))

    facts = [] # processed output of rephrase_and_score
    searchQuerys = generate_search_queries( claims=topClaims, client=client)
    print(json.dumps(searchQuerys, indent=4))