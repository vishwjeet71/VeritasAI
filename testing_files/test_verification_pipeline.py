import pytest
from unittest.mock import patch, MagicMock
from backend.verification_pipeline import verification


# Fixture

@pytest.fixture
def verifier():
    v = verification()

    # mock transformer
    v.tf = MagicMock()

    # mock search handler
    v.sf = MagicMock()

    return v


# Test: _fail method

def test_fail_method(verifier):
    result = verifier._fail(
        claim="Earth is flat",
        method="test",
        user_msg="error happened",
        dev_msg="debug info"
    )

    assert result["claim"] == "Earth is flat"
    assert result["verdict"] == "Error"
    assert result["method"] == "test"


# Test: invalid input handling

def test_input_handler_invalid_input(verifier):

    result = verifier.input_handler("")

    assert result["verdict"] == "Error"
    assert "valid text claim" in result["explanation"]


# Test: query classification

@patch("verification_pipeline.classify_input")
@patch("verification_pipeline.rephrase_and_score")
@patch.object(verification, "verify_claim")
def test_input_handler_query(
    mock_verify_claim,
    mock_rephrase,
    mock_classify,
    verifier
):

    mock_classify.return_value = {"type": "query"}

    mock_rephrase.return_value = [
        {
            "claim": "Sky is blue",
            "score": 0.95
        }
    ]

    mock_verify_claim.return_value = {
        "claim": "Sky is blue",
        "verdict": "True"
    }

    result = verifier.input_handler("Sky is blue")

    assert result["verdict"] == "True"
    mock_verify_claim.assert_called_once()


# Test: verify_claim success

@patch("verification_pipeline.generate_search_queries")
@patch("verification_pipeline.check_claim_in_db")
@patch("verification_pipeline.generate_verdict")
def test_verify_claim_success(
    mock_verdict,
    mock_db,
    mock_queries,
    verifier
):

    mock_queries.return_value = [
        {
            "fact_check_query": "query",
            "gnews_specific": "news1",
            "gnews_broad": "news2"
        }
    ]

    mock_db.return_value = {
        "title": {
            "source": "https://example.com"
        }
    }

    verifier.tf.extract_evidence.return_value = [
        "some evidence"
    ]

    mock_verdict.return_value = {
        "verdict": "True",
        "explanation": "verified",
        "sources": ["https://example.com"]
    }

    result = verifier.verify_claim("Sky is blue")

    assert result["verdict"] == "True"
    assert result["method"] == "fact check db"


# Test: fallback to search pipeline

@patch("verification_pipeline.generate_search_queries")
@patch("verification_pipeline.check_claim_in_db")
@patch("verification_pipeline.generate_verdict")
def test_fallback_search_pipeline(
    mock_verdict,
    mock_db,
    mock_queries,
    verifier
):

    mock_queries.return_value = [
        {
            "fact_check_query": "query",
            "gnews_specific": "news1",
            "gnews_broad": "news2"
        }
    ]

    # DB failed / empty
    mock_db.return_value = None

    verifier.sf.gnews.return_value = {
        1: {
            "url": "https://news.com"
        }
    }

    verifier.tf.extract_evidence.return_value = [
        "evidence"
    ]

    mock_verdict.return_value = {
        "verdict": "False",
        "explanation": "done",
        "sources": ["https://news.com"]
    }

    result = verifier.verify_claim("fake claim")

    assert result["method"] == "search pipeline"
    assert result["verdict"] == "False"


# Test: search query generation failure

@patch("verification_pipeline.generate_search_queries")
def test_generate_search_queries_failure(
    mock_queries,
    verifier
):

    mock_queries.side_effect = Exception("API Error")

    result = verifier.verify_claim("some claim")

    assert result["verdict"] == "Error"


# Test: evidence extraction failure

@patch("verification_pipeline.generate_search_queries")
@patch("verification_pipeline.check_claim_in_db")
def test_extract_evidence_failure(
    mock_db,
    mock_queries,
    verifier
):

    mock_queries.return_value = [
        {
            "fact_check_query": "query",
            "gnews_specific": "news1",
            "gnews_broad": "news2"
        }
    ]

    mock_db.return_value = {
        "title": {
            "source": "https://example.com"
        }
    }

    verifier.tf.extract_evidence.side_effect = Exception("extract fail")

    result = verifier.verify_claim("claim")

    assert result["verdict"] == "Error"


# Test: batch verification

@patch.object(verification, "verify_claim")
def test_verify_claims_batch(
    mock_verify_claim,
    verifier
):

    claims = [
        "claim 1",
        "claim 2"
    ]

    mock_verify_claim.return_value = {
        "verdict": "True"
    }

    # simplified batch mock
    with patch(
        "verification_pipeline.generate_search_queries"
    ) as mock_queries:

        mock_queries.return_value = [
            {
                "fact_check_query": "q1",
                "gnews_specific": "n1",
                "gnews_broad": "n2"
            },
            {
                "fact_check_query": "q2",
                "gnews_specific": "n3",
                "gnews_broad": "n4"
            }
        ]

        verifier.tf.extract_evidence.return_value = [
            "evidence"
        ]

        verifier.sf.gnews.return_value = {
            1: {
                "url": "https://news.com"
            }
        }

        with patch(
            "verification_pipeline.generate_verdict"
        ) as mock_verdict:

            mock_verdict.return_value = {
                "verdict": "True",
                "sources": []
            }

            result = verifier.verify_claims_batch(claims)

            assert len(result) == 2