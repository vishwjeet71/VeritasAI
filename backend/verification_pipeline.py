from fact_check_db import check_claim_in_db
from groq_client import generate_search_queries, generate_verdict, client, rephrase_and_score
import json, logging, traceback
from evidence_extractor import Transformer
from search_handler import search_and_filter
from input_handler import classify_input
from article_fetcher import fetch_article
from claim_extractor import extract_candidate_sentences

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


    def input_handler(self, user_input: str):

        if not isinstance(user_input, str) or not user_input.strip():
            return self._fail(
                claim=str(user_input),
                method=None,
                user_msg="Please enter a valid text claim or article URL.",
                dev_msg=f"input_handler received invalid input: type={type(user_input)}, value={repr(user_input)}",
            )

        try:
            input_type = classify_input(user_input=user_input)
        except Exception as e:
            return self._fail(
                claim=user_input,
                method=None,
                user_msg="We couldn't process your input. Please try again.",
                dev_msg=f"classify_input raised for input: {repr(user_input)}",
                exc=e,
            )

    
        if input_type.get("type") == "query":
            try:
                valid_claims = rephrase_and_score(candidates=[user_input])
            except Exception as e:
                return self._fail(
                    claim=user_input,
                    method=None,
                    user_msg="We couldn't analyse your input. Please try rephrasing it.",
                    dev_msg=f"rephrase_and_score raised for query: {repr(user_input)}",
                    exc=e,
                )

            if not valid_claims:
                return self._fail(
                    claim=user_input,
                    method=None,
                    user_msg="No verifiable factual claims found. Try entering a factual statement or an article URL.",
                    dev_msg=f"rephrase_and_score returned empty for query: {repr(user_input)}",
                )

            if len(valid_claims) == 1:
                return self.verify_claim(claim=valid_claims[0]["claim"])

            top_5_claims = [
                item["claim"]
                for item in sorted(valid_claims, key=lambda x: x["score"], reverse=True)[:5]
            ]
            return top_5_claims  # return to frontend for user claim selection


        if input_type.get("type") == "url":
            try:
                raw_article, fetch_error = fetch_article([user_input])[0]
            except Exception as e:
                return self._fail(
                    claim=user_input,
                    method=None,
                    user_msg="We couldn't fetch the article. Check the URL and try again.",
                    dev_msg=f"fetch_article raised for url: {repr(user_input)}",
                    exc=e,
                )

            if not raw_article:
                return self._fail(
                    claim=user_input,
                    method=None,
                    user_msg="We couldn't read the article at that URL. It may be paywalled, unavailable, or unsupported.",
                    dev_msg=f"fetch_article failed for url: {repr(user_input)} | fetch_error: {fetch_error}",
                )

            try:
                candidates = extract_candidate_sentences(raw_article)
            except Exception as e:
                return self._fail(
                    claim=user_input,
                    method=None,
                    user_msg="We fetched the article but couldn't extract any claims from it.",
                    dev_msg=f"extract_candidate_sentences raised for url: {repr(user_input)}",
                    exc=e,
                )

            if not candidates:
                return self._fail(
                    claim=user_input,
                    method=None,
                    user_msg="No verifiable claims found in the article.",
                    dev_msg=f"extract_candidate_sentences returned empty for url: {repr(user_input)}",
                )

            try:
                valid_claims = rephrase_and_score(candidates=candidates)
            except Exception as e:
                return self._fail(
                    claim=user_input,
                    method=None,
                    user_msg="We extracted content from the article but couldn't score the claims.",
                    dev_msg=f"rephrase_and_score raised for url path | url: {repr(user_input)}",
                    exc=e,
                )

            if not valid_claims:
                return self._fail(
                    claim=user_input,
                    method=None,
                    user_msg="No verifiable claims could be extracted from this article.",
                    dev_msg=f"rephrase_and_score returned empty for url: {repr(user_input)}",
                )

            top_5_claims = [
                item["claim"]
                for item in sorted(valid_claims, key=lambda x: x["score"], reverse=True)[:5]
            ]
            return top_5_claims  # return to frontend for user claim selection

    
        return self._fail(
            claim=user_input,
            method=None,
            user_msg="We couldn't understand your input. Please enter a factual claim or a valid article URL.",
            dev_msg=f"classify_input returned unrecognised type: {input_type} for input: {repr(user_input)}",
        )

if __name__ == "__main__":
    vc = verification()
    print(vc.input_handler(""))