import pytest
from spacy.language import Language

from backend.claim_extractor import (
    load_nlp_model, extract_from_query,
    extract_candidate_sentences
)

# Model loading

def test_load_nlp_model():
    model = load_nlp_model()

    assert isinstance(model, Language)
    

# candidate sentences

@pytest.mark.parametrize(
    "article_text, expected_empty",
    [
        ("Apple released a new iPhone. The weather is good.", False),
        ("@!#*^$#*&#", True),
        (" ", True),
    ]
)
def test_candidate_sentences(article_text, expected_empty):

    result = extract_candidate_sentences(article_text)

    assert isinstance(result, list)

    if expected_empty:
        assert len(result) == 0
    else:
        assert len(result) > 0


# input -> query

def test_extract_from_query(mocker):

    mock_response = mocker.Mock()

    mock_response.choices = [
        mocker.Mock(
            message=mocker.Mock(
                content='''[{ "claim": "claim.", "score": 0.95 }]'''
            )
        )
    ]

    mock_client = mocker.Mock()

    mock_client.chat.completions.create.return_value = mock_response

    result = extract_from_query(
        query="query",
        client=mock_client
    )

    assert result == [{ "claim": "claim.", "score": 0.95 }]

    mock_client.chat.completions.create.assert_called_once()


# Error Testiing

class FakeAuthError(Exception):
    pass

class Test_errors:
    def test_extract_from_query_auth_error(self, mocker):

        mock_client = mocker.Mock()

        mock_client.chat.completions.create.side_effect = (
            FakeAuthError("Invalid API key")
        )

        result = extract_from_query(
            query="query",
            client=mock_client
        )

        assert result == []

    def test_extract_from_query_other_error(self, mocker):
        mock_client = mocker.Mock()

        mock_client.chat.completions.create.side_effect = Exception(
            "Somthing wrrong")
        
        result = extract_from_query(
            query="query",
            client=mock_client
        )

        assert result == []