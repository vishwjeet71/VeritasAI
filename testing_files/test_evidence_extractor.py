import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from backend.evidence_extractor import Transformer


# get_embeddings() 

def test_get_embeddings_invalid_input():
    transformer = Transformer()

    result = transformer.get_embeddings(12345)

    assert result is None


@patch("backend.evidence_extractor.SentenceTransformer")
def test_get_embeddings_model_exception(mock_model):
    mock_instance = mock_model.return_value
    mock_instance.encode.side_effect = Exception("Encoding failed")

    transformer = Transformer()

    result = transformer.get_embeddings("test text")

    assert result is None


@patch("backend.evidence_extractor.SentenceTransformer")
def test_get_embeddings_success(mock_model):
    mock_instance = mock_model.return_value
    mock_instance.encode.return_value = np.array([0.1, 0.2, 0.3])

    transformer = Transformer()

    result = transformer.get_embeddings("hello")

    assert result is not None
    assert isinstance(result, np.ndarray)


# extract_evidence()

@patch("backend.evidence_extractor.fetch_article")
def test_extract_evidence_invalid_article(fetch_mock):
    fetch_mock.return_value = [
        (None, "Invalid article")
    ]

    transformer = Transformer()

    result = transformer.extract_evidence(
        "sample claim",
        ["https://example.com"]
    )

    assert result is None


@patch("backend.evidence_extractor.fetch_article")
@patch("backend.evidence_extractor.spacyModel")
def test_extract_evidence_spacy_exception(
    spacy_mock,
    fetch_mock
):
    fetch_mock.return_value = [
        ("some article text", "url")
    ]

    spacy_mock.side_effect = Exception("Spacy failed")

    transformer = Transformer()

    result = transformer.extract_evidence(
        "claim",
        ["https://example.com"]
    )

    assert result is None


@patch("backend.evidence_extractor.fetch_article")
@patch("backend.evidence_extractor.spacyModel")
@patch.object(Transformer, "get_embeddings")
def test_extract_evidence_embedding_failure(
    embedding_mock,
    spacy_mock,
    fetch_mock
):
    fetch_mock.return_value = [
        ("article text", "url")
    ]

    mock_doc = MagicMock()
    mock_doc.sents = [
        MagicMock(text="Sentence 1"),
        MagicMock(text="Sentence 2")
    ]

    spacy_mock.return_value = mock_doc

    # claim embedding fails
    embedding_mock.side_effect = [None, np.array([[1, 2], [3, 4]])]

    transformer = Transformer()

    result = transformer.extract_evidence(
        "claim",
        ["https://example.com"]
    )

    assert result is None


@patch("backend.evidence_extractor.fetch_article")
@patch("backend.evidence_extractor.spacyModel")
@patch.object(Transformer, "get_embeddings")
def test_extract_evidence_success(
    embedding_mock,
    spacy_mock,
    fetch_mock
):
    fetch_mock.return_value = [
        ("article text", "url")
    ]

    mock_doc = MagicMock()
    mock_doc.sents = [
        MagicMock(text="Sentence 1"),
        MagicMock(text="Sentence 2"),
        MagicMock(text="Sentence 3")
    ]

    spacy_mock.return_value = mock_doc

    claim_embedding = np.array([1.0, 1.0])

    sentence_embeddings = np.array([
        [1.0, 1.0],
        [0.5, 0.5],
        [0.1, 0.1]
    ])

    embedding_mock.side_effect = [
        claim_embedding,
        sentence_embeddings
    ]

    transformer = Transformer()

    result = transformer.extract_evidence(
        "claim",
        ["https://example.com"]
    )

    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 2