from sentence_transformers import SentenceTransformer
import logging, numpy as np
from transformers import logging as hf_logging
from backend.claim_extractor import NLP as spacyModel
from backend.article_fetcher import fetch_article

hf_logging.set_verbosity_error()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Transformer:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def get_embeddings(self, text):
        if not isinstance(text, (str, list)):
            return None
        
        try:
            embeddings = self.model.encode(text)
            return embeddings
        except Exception as e:
            logger.error(f"[evidenceExtractor] unexpected error: {e}")
            return None

    def extract_evidence(self, claim: str, source_urls: list[str]):
        text_chunks = []

        articals = fetch_article(source_urls)
        for artical in articals:
            if artical[0] == None:
                logger.warning(f"{artical[1]}")
                continue

            try:
                doc = spacyModel(artical[0])
                sentences = [sent.text for sent in doc.sents]

                claim_emb = self.get_embeddings(claim)
                sentences_embs = self.get_embeddings(sentences)
            except Exception as e:
                logger.error(f"[evidenceExtractor] unexpected error: {e}")
                continue
            

            if claim_emb is None or sentences_embs is None:
                continue

            dot_product = np.dot(sentences_embs, claim_emb)

            norm_claim = np.linalg.norm(claim_emb)
            norm_sentences = np.linalg.norm(sentences_embs, axis=1)

            scores = dot_product / (norm_claim * norm_sentences)
            top_3_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:2]


            for index in top_3_indices:
                text_chunks.append(sentences[index])
        
        if text_chunks:
            return text_chunks
        else:
            return None