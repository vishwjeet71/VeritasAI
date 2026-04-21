from prompts import REPHRASE_AND_SCORE_PROMPT, SEARCH_QUERY_PROMPT, VERDICT_PROMPT
import logging, groq, json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rephrase_and_score(
        candidates: list[str],
        model_name = "llama-3.3-70b-versatile"
        ) -> list[dict]:
    
    if not isinstance(candidates, list) or len(candidates) == 0:
        logger.error("[rephraseAndScore] Invalid input: candidates must be a non-empty list")
        return []

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
        if hasattr(e, 'body') and isinstance(e.body, dict):
            reason = e.body.get("error", {}).get("message", "Invalid API Key")
        else:
            reason = str(e)
        logger.error(f"[rephraseAndScore] Authentication error: {reason}")
        return []
    
    except Exception as e:
        if hasattr(e, 'body') and isinstance(e.body, dict):
            reason = e.body.get("error", {}).get("message", "unknown error")
        else:
            reason = str(e)
        logger.error(f"[rephraseAndScore] unexpected Error during verdictGeneration processing: {reason}")
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
        model_name: str = "llama-3.3-70b-versatile"
        ) -> list[dict]:
    
    if not isinstance(claims, list) or len(claims) == 0:
        logger.error("[searchQueries] Invalid input: claims must be a non-empty list")
        return []
    
    numbered = "\n".join(
        [f"{i+1}. {claim}" for i, claim in enumerate(claims)]
    )
    prompt = SEARCH_QUERY_PROMPT.replace("{claims}", numbered)

    try:

        response = client.chat.completions.create(
            model= model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
    except groq.AuthenticationError as e:
        if hasattr(e, 'body') and isinstance(e.body, dict):
            reason = e.body.get("error", {}).get("message", "Invalid API Key")
        else:
            reason = str(e)
        logger.error(f"[searchQueries] Authentication error: {reason}")
        return []
    
    except Exception as e:
        if hasattr(e, 'body') and isinstance(e.body, dict):
            reason = e.body.get("error", {}).get("message", "unknown error")
        else:
            reason = str(e)
        logger.error(f"[searchQueries] unexpected Error during verdictGeneration processing: {reason}")
        return []

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
    if not isinstance(evidence_chunks, list) or not isinstance(source_urls, list):
        logger.error("[generate_verdict] Invalid input: evidence_chunks and source_urls must be lists")
        return None
    
    if len(evidence_chunks) == 0 or len(source_urls) == 0:
        logger.warning("[generate_verdict] get null input")
        return None

    formatted_chunks = "\n".join(
        [f"[Chunk {i+1} from {source_urls[i] if i < len(source_urls) else 'unknown'}]:\n{chunk}"
         for i, chunk in enumerate(evidence_chunks)]
    )

    formatted_urls = "\n".join([f"- {url}" for url in source_urls])

    prompt = (VERDICT_PROMPT
              .replace("{claim}", claim)
              .replace("{evidence_chunks}", formatted_chunks)
              .replace("{source_urls}", formatted_urls))
    
    try:
        response = client.chat.completions.create(
            model= model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, 
        )
    except groq.AuthenticationError as e:
        if hasattr(e, 'body') and isinstance(e.body, dict):
            reason = e.body.get("error", {}).get("message", "Invalid API Key")
        else:
            reason = str(e)
        logger.error(f"[generateVerdict] Authentication error: {reason}")
        return []
    
    except Exception as e:
        if hasattr(e, 'body') and isinstance(e.body, dict):
            reason = e.body.get("error", {}).get("message", "unknown error")
        else:
            reason = str(e)
        logger.error(f"[generateVerdict] unexpected Error during verdictGeneration processing: {reason}")
        return []

    raw = response.choices[0].message.content.strip()
    result = json.loads(raw)

    valid_verdicts = {"Supported", "Contradicted", "Inconclusive", "Unverifiable"}
    if result.get("verdict") not in valid_verdicts:
        result["verdict"] = "Inconclusive"

    return result

# --- Testing ---
if __name__ == "__main__":

    client = groq.Groq(api_key= "")

    candidates = [] # output of extract_candidate_sentences
    topClaims = rephrase_and_score(candidates=candidates)
    print(json.dumps(topClaims, indent=4))

    facts = [] # processed output of rephrase_and_score
    searchQuerys = generate_search_queries( claims=topClaims)
    print(json.dumps(searchQuerys, indent=4))

    claim = ""
    evidence_chunks = []
    source_urls = []
    print(json.dumps(generate_verdict(claim=claim, evidence_chunks=evidence_chunks, source_urls=source_urls), indent=4))