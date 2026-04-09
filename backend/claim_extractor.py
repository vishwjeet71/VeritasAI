import spacy
from spacy.tokens import Span, Doc
from spacy.util import is_package
from typing import List, Optional, Set
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_nlp_model(model_name: str = "en_core_web_md"): # en_core_web_md

    if not is_package(model_name):
        print(f"Downloading {model_name}...")
        spacy.cli.download(model_name)

    try:
        nlp = spacy.load(model_name, disable=["lemmatizer", "textcat"])
        return nlp
    except Exception as e:
        logger.error(f"Failed to load spaCy model {model_name}: {e}")
        return None

NLP = load_nlp_model()

def _is_part_of_entity(token, sent: Span) -> bool:
    return any(token.i >= ent.start and token.i < ent.end for ent in sent.ents)

def extract_candidate_sentences(
    article_text: str, 
    min_tokens: int = 5,
    strict_mode: bool = False
) -> List[str]:
    
    if not isinstance(article_text, str) or not article_text.strip():
        return []

    if NLP is None:
        logger.error("NLP model is not initialized.")
        return []

    try:
        doc = NLP(article_text)
    except Exception as e:
        logger.error(f"Error during NLP processing: {e}")
        return []

    candidate_sentences = []
    seen_hashes: Set[int] = set()

    for sent in doc.sents:

        if len(sent) < min_tokens:
            continue

        if sent.text.strip().endswith("?") or not any(t.is_punct for t in sent):
            continue

        # Must have at least one main verb
        has_verb = any(t.pos_ == "VERB" for t in sent)
        if not has_verb:
            continue

        # Semantic Pattern Matching
        match_score = 0
        ents = {ent.label_ for ent in sent.ents}
        
        # Pattern 1 & 3: Entity + Action / Entity + Relationship
        has_entity_subject = any(
            t.dep_ == "nsubj" and t.head.pos_ == "VERB" and _is_part_of_entity(t, sent)
            for t in sent
        )
        if has_entity_subject:
            match_score += 1

        # Pattern 2: Entity + Attribute/State (Numbers, Percents)
        has_stats = any(label in ents for label in ["CARDINAL", "PERCENT", "QUANTITY", "MONEY"])
        has_entity = any(label in ents for label in ["ORG", "PERSON", "GPE", "PRODUCT"])
        if has_stats and has_entity:
            match_score += 1

        # Pattern 4: Event + Time/Place
        has_context = any(label in ents for label in ["DATE", "TIME", "GPE", "LOC", "FAC"])
        if has_verb and has_context:
            match_score += 2

        threshold = 2 if strict_mode else 1
        if match_score >= threshold:
            sent_text = sent.text.strip()
            sent_hash = hash(sent_text)
            
            if sent_hash not in seen_hashes:
                candidate_sentences.append(sent_text)
                seen_hashes.add(sent_hash)

    return candidate_sentences


def extract_and_score_claims(candidates):
    pass

def extract_claims_from_query(query):
    pass


# --- Testing ---
if __name__ == "__main__":
    raw_text = str(input("Enter text: "))
    results = extract_candidate_sentences(raw_text)

    for i, s in enumerate(results):
        print(f"{i+1}. {s}")