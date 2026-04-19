from sentence_transformers import SentenceTransformer
import logging
from transformers import logging as hf_logging

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

if __name__ == "__main__":
    tf = Transformer()
    print(tf.get_embeddings(["hello world"]))