import pytest, groq, httpx, json
from backend.groq_client import rephrase_and_score, generate_search_queries, generate_verdict

def AuthenticationError(Exception):
    pass

# rephrase_and_score

class Test_rephrase_and_score:

    def test_input_handling(self, mocker):
        dummy_client = mocker.Mock()

        dummy_client.chat.completions.create.return_value = []
        result = rephrase_and_score(
            client=dummy_client,
            candidates=[]
        )
        assert result == []

    def test_auth_error(self, mocker):
        dummy_client = mocker.Mock()
        dummy_error = mocker.Mock()

        dummy_error.body = {"error": {"message": "Invalid API key"}}


        request = httpx.Request(
            method="POST",
            url="https://api.groq.com/openai/v1/chat/completions"
        )

        response = httpx.Response(
            status_code=401,
            request=request
        )

        dummy_client.chat.completions.create.side_effect = (
            groq.AuthenticationError(
                message="Invalid API key",
                response=response,
                body={"error": {"message": "Invalid API key"}}
            )
        )

        result = rephrase_and_score(
            client=dummy_client,
            candidates=["candidate_1", "candidate_2"]
        )
        
        assert result == []

    def test_other_error(self, mocker):
        dummy_client = mocker.Mock()
        dummy_error = mocker.Mock()
        dummy_error.body = {"error": {"message": "Somthing wrrong"}}

        request = httpx.Request(
            method="POST",
            url="https://api.groq.com/openai/v1/chat/completions"
        )

        response = httpx.Response(
            status_code=400,
            request=request
        )

        dummy_client.chat.completions.create.side_effect = (
            Exception(dummy_error)
        )   

        result = rephrase_and_score(
            client=dummy_client,
            candidates=["candidate_1", "candidate_2"]
        )

        assert result == []

    def test_success(self, mocker):
        dummy_client = mocker.Mock()
        dummy_response = mocker.Mock()

        dummy_response.choices = [
            mocker.Mock(
                message=mocker.Mock(
                    content='''[
                        {"claim": "claim.", "score": 0.95},
                        {"claim": "claim..", "score": 0.90}
                    ]'''
                )
            )
        ]

        dummy_client.chat.completions.create.return_value = dummy_response

        result = rephrase_and_score(
            dummy_client,
            candidates = ["candidate_1", "candidate_2"]
        )

        assert result == [
            {"claim": "claim.", "score": 0.95},
            {"claim": "claim..", "score": 0.90}
        ]
        dummy_client.chat.completions.create.assert_called_once()


# generate_search_queries

class Test_generate_search_queries:
    
    @pytest.mark.parametrize("input, expected_output", [
        (None, []),
        ("string_as_input", []),
        ([],[])
        ]
    )
    def test_input_handling(self, mocker, expected_output, input):
        dummy_client = mocker.Mock()

        dummy_client.chat.completions.create.return_value = []
        result = generate_search_queries(
            client=dummy_client,
            claims=input
        )
        assert result == expected_output
    
    def test_auth_error(self, mocker):
        dummy_client = mocker.Mock()
        dummy_error = mocker.Mock()

        dummy_error.body = {"error": {"message": "Invalid API key"}}


        request = httpx.Request(
            method="POST",
            url="https://api.groq.com/openai/v1/chat/completions"
        )
        response = httpx.Response(
            status_code=401,
            request=request
        )

        dummy_client.chat.completions.create.side_effect = (
            groq.AuthenticationError(
                message="Invalid API key",
                response=response,
                body=dummy_error
            )
        )

        result = rephrase_and_score(
            client=dummy_client,
            candidates=["claim_1", "claim_2"]
        )
        assert result == []

    def test_other_error(self, mocker):
        dummy_client = mocker.Mock()
        dummy_error = mocker

        dummy_error.body = {"error": {"message": "Somthing wrrong"}}

        request = httpx.Request(
            method="POST",
            url="https://api.groq.com/openai/v1/chat/completions"
        )

        repose = httpx.Response(
            status_code=400,
            request=request
        )

        dummy_client.chat.completions.create.side_effect = (
            Exception(dummy_error)
        )

        result = rephrase_and_score(
            client=dummy_client,
            candidates=["claim_1", "claim_2"]
        )
        assert result == []
        
    def test_success(self, mocker):
        dummy_client = mocker.Mock()
        dummy_response = mocker.Mock()

        dummy_response.choices = [
            mocker.Mock(
                message=mocker.Mock(
                    content='''[{
                        "claim": "claim string",
                        "fact_check_query": "query for fact check db",
                        "gnews_specific": "short keyword query",
                        "gnews_broad": "broader fallback keyword query"
                    }]'''
                )
            )
        ]

        dummy_client.chat.completions.create.return_value = dummy_response

        result = generate_search_queries(
            client=dummy_client,
            claims=["claim_1", "claim_2"]
        )

        assert result == [{
                        "claim": "claim string",
                        "fact_check_query": "query for fact check db",
                        "gnews_specific": "short keyword query",
                        "gnews_broad": "broader fallback keyword query"
                    }]
        
        dummy_client.chat.completions.create.assert_called_once()


# generate_verdict

class TestGenerateVerdict:

    @pytest.mark.parametrize(
        "evidence_chunks, source_urls",
        [
            (None, None),
            (" ", " "),
            ([], []),
        ],
    )
    def test_invalid_inputs_return_none(
        self,
        mocker,
        evidence_chunks,
        source_urls
    ):
        dummy_client = mocker.Mock()

        result = generate_verdict(
            client=dummy_client,
            claim="claim",
            evidence_chunks=evidence_chunks,
            source_urls=source_urls
        )

        assert result is None
        dummy_client.chat.completions.create.assert_not_called()

    def test_valid_response(
        self,
        mocker
    ):
        dummy_client = mocker.Mock()

        mock_response = mocker.Mock()
        mock_response.choices = [
            mocker.Mock(
                message=mocker.Mock(
                    content=json.dumps({
                        "Claim": "Claim",
                        "verdict": "Supported",
                        "explanation": "Explanation",
                        "Source Urls": ["url1"]
                    })
                )
            )
        ]

        dummy_client.chat.completions.create.return_value = mock_response

        result = generate_verdict(
            client=dummy_client,
            claim="claim",
            evidence_chunks=["chunk"],
            source_urls=["url"]
        )

        assert result == {
            "Claim": "Claim",
            "verdict": "Supported",
            "explanation": "Explanation",
            "Source Urls": ["url1"]
        }

        dummy_client.chat.completions.create.assert_called_once()

    def test_invalid_verdict_defaults_to_inconclusive(
        self,
        mocker
    ):
        dummy_client = mocker.Mock()

        mock_response = mocker.Mock()
        mock_response.choices = [
            mocker.Mock(
                message=mocker.Mock(
                    content=json.dumps({
                        "Claim": "Claim",
                        "verdict": "Random Verdict",
                        "explanation": "Explanation",
                        "Source Urls": ["url1"]
                    })
                )
            )
        ]

        dummy_client.chat.completions.create.return_value = mock_response

        result = generate_verdict(
            client=dummy_client,
            claim="claim",
            evidence_chunks=["chunk"],
            source_urls=["url"]
        )

        assert result["verdict"] == "Inconclusive"

    def test_authentication_error_returns_empty_list(
        self,
        mocker
    ):
        dummy_client = mocker.Mock()

        request = httpx.Request(
            method="POST",
            url="https://api.groq.com/openai/v1/chat/completions"
        )

        response = httpx.Response(
            status_code=401,
            request=request
        )

        auth_error = groq.AuthenticationError(
            message="Invalid API Key",
            response=response,
            body={
                "error": {
                    "message": "Invalid API Key"
                }
            }
        )

        dummy_client.chat.completions.create.side_effect = auth_error

        result = generate_verdict(
            client=dummy_client,
            claim="claim",
            evidence_chunks=["chunk"],
            source_urls=["url"]
        )

        assert result == []

    def test_unexpected_exception_returns_empty_list(
        self,
        mocker
    ):
        dummy_client = mocker.Mock()

        dummy_client.chat.completions.create.side_effect = Exception(
            "Unexpected failure"
        )

        result = generate_verdict(
            client=dummy_client,
            claim="claim",
            evidence_chunks=["chunk"],
            source_urls=["url"]
        )

        assert result == []

    def test_invalid_json_raises_json_decode_error(
        self,
        mocker
    ):
        dummy_client = mocker.Mock()

        mock_response = mocker.Mock()
        mock_response.choices = [
            mocker.Mock(
                message=mocker.Mock(
                    content="INVALID_JSON"
                )
            )
        ]

        dummy_client.chat.completions.create.return_value = mock_response

        with pytest.raises(json.JSONDecodeError):

            generate_verdict(
                client=dummy_client,
                claim="claim",
                evidence_chunks=["chunk"],
                source_urls=["url"]
            )