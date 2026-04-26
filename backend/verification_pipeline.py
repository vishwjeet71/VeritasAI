from fact_check_db import check_claim_in_db
from groq_client import generate_search_queries, generate_verdict, client
import json, logging, traceback
from evidence_extractor import Transformer
from search_handler import search_and_filter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class verification:
    def __init__(self):
        self.tf = Transformer()
        self.sf = search_and_filter()


    def _fail(self, claim: str, method: str | None, user_msg: str, dev_msg: str, exc: Exception = None) -> dict:
        """Return a structured failure result and log developer detail."""
        log_line = f"[verify_claim] {dev_msg}"
        if exc:
            log_line += f" | Exception: {exc} | Traceback: {traceback.format_exc()}"
        logger.error(log_line)
        return {
            "claim":       claim,
            "verdict":     "Error",
            "explanation": user_msg,
            "sources":     [],
            "method":      method,
        }


    def verify_claim(self, claim: str) -> dict:
        method = None

        try:
            searchQuerys = generate_search_queries(claims=[claim])
            if not searchQuerys:
                return self._fail(
                    claim, method,
                    user_msg="We couldn't process this claim right now. Please try rephrasing it.",
                    dev_msg=f"generate_search_queries returned empty for claim: {repr(claim)}",
                )
            fact_check_query = searchQuerys[0].get("fact_check_query")
            gnews_specific   = searchQuerys[0].get("gnews_specific")
            gnews_broad      = searchQuerys[0].get("gnews_broad")
        except Exception as e:
            return self._fail(
                claim, method,
                user_msg="We couldn't process this claim right now. Please try rephrasing it.",
                dev_msg=f"generate_search_queries raised for claim: {repr(claim)}",
                exc=e,
            )


        # fact-check DB 
        try:
            db_output = check_claim_in_db(claim=claim, searchQuerys=[fact_check_query], embedding_obj=self.tf)
        except Exception as e:
            db_output = None
            logger.warning(f"[verify_claim] fact-check DB call failed, falling through to search | claim: {repr(claim)} | {e}")

        if db_output:
            Links  = [data.get("source") for title, data in db_output.items()]
            method = "fact check db"
        else:
            # search pipeline
            try:
                search_results = self.sf.gnews([gnews_specific])
                if not search_results:
                    search_results = self.sf.gnews([gnews_broad])
            except Exception as e:
                return self._fail(
                    claim, method,
                    user_msg="We couldn't find relevant sources for this claim. Please try again later.",
                    dev_msg=f"gnews search raised for claim: {repr(claim)}",
                    exc=e,
                )

            if not search_results:
                return self._fail(
                    claim, method,
                    user_msg="We couldn't find reliable sources to verify this claim.",
                    dev_msg=f"Both gnews_specific and gnews_broad returned no results for claim: {repr(claim)}",
                )

            Links  = [data.get("url") for id, data in search_results.items()]
            method = "search pipeline"

        # evidence extraction
        try:
            evidence = self.tf.extract_evidence(claim=claim, source_urls=Links)
        except Exception as e:
            return self._fail(
                claim, method,
                user_msg="We found sources but couldn't extract usable content from them.",
                dev_msg=f"extract_evidence raised for claim: {repr(claim)} | urls: {Links}",
                exc=e,
            )

        if not evidence:
            return self._fail(
                claim, method,
                user_msg="We found sources but couldn't extract usable content from them.",
                dev_msg=f"extract_evidence returned empty for claim: {repr(claim)} | urls: {Links}",
            )

        # verdict generation
        try:
            verdict = generate_verdict(claim=claim, evidence_chunks=evidence, source_urls=Links)
        except Exception as e:
            return self._fail(
                claim, method,
                user_msg="Verification failed at the final step. Please try again.",
                dev_msg=f"generate_verdict raised for claim: {repr(claim)}",
                exc=e,
            )

        if not verdict:
            return self._fail(
                claim, method,
                user_msg="Verification failed at the final step. Please try again.",
                dev_msg=f"generate_verdict returned empty/None for claim: {repr(claim)}",
            )

        verdict["method"] = method
        verdict["claim"]  = claim
        return verdict


if __name__ == "__main__":
    vc = verification()
    claims = [
    ]
    claim = claims[1]
    print(json.dumps(vc.verify_claim(claim), indent=4))