# test_search_and_filter.py

import pytest
from unittest.mock import patch, Mock
from backend.search_handler import search_and_filter

@pytest.fixture
def sf():
    return search_and_filter()


# TEST _load_credibility_scores

@patch("backend.search_handler.get_credibility_scorer")
def test_load_credibility_scores_success(mock_scorer, sf):

    mock_scorer.return_value = {
        "BBC": 90,
        "CNN": 80
    }

    result = sf._load_credibility_scores({"BBC", "CNN"})

    assert result == {
        "BBC": 90,
        "CNN": 80
    }

def test_load_credibility_scores_invalid_input(sf):

    result = sf._load_credibility_scores(["BBC"])

    assert result == {}



# TEST GNEWS

@patch("backend.search_handler.requests.get")
@patch.object(search_and_filter, "_load_credibility_scores")
def test_gnews_success(mock_scores, mock_get, sf):

    mock_scores.return_value = {
        "BBC": 95,
        "CNN": 85
    }

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "articles": [
            {
                "id": "1",
                "source": {"name": "BBC"},
                "url": "https://bbc.com/news1"
            },
            {
                "id": "2",
                "source": {"name": "CNN"},
                "url": "https://cnn.com/news2"
            }
        ]
    }

    mock_get.return_value = mock_response

    result = sf.gnews(["AI News"])

    assert len(result) > 0
    assert "1" in result
    assert result["1"]["name"] == "BBC"


@patch("backend.search_handler.requests.get")
def test_gnews_invalid_api(mock_get, sf):

    mock_response = Mock()
    mock_response.status_code = 401

    mock_get.return_value = mock_response

    result = sf.gnews(["AI"])

    assert result == {}


def test_gnews_invalid_input(sf):

    result = sf.gnews("invalid")

    assert result == {}


def test_gnews_empty_input(sf):

    result = sf.gnews([])

    assert result == {}


# TEST SERPERDEV

@patch("backend.search_handler.requests.request")
@patch.object(search_and_filter, "_load_credibility_scores")
def test_serperdev_success(mock_scores, mock_request, sf):

    mock_scores.return_value = {
        "Reuters": 98,
        "BBC": 90
    }

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "news": [
            {
                "source": "Reuters",
                "link": "https://reuters.com/news"
            },
            {
                "source": "BBC",
                "link": "https://bbc.com/news"
            }
        ]
    }

    mock_request.return_value = mock_response

    result = sf.serperdev(
        ["AI News"],
        serperdevApi="fake_api"
    )

    assert len(result) > 0


@patch("backend.search_handler.requests.request")
def test_serperdev_invalid_api(mock_request, sf):

    mock_response = Mock()
    mock_response.status_code = 401

    mock_request.return_value = mock_response

    result = sf.serperdev(
        ["AI"],
        serperdevApi="fake_api"
    )

    assert result == {}


def test_serperdev_invalid_input(sf):

    result = sf.serperdev(
        "invalid",
        serperdevApi="fake_api"
    )

    assert result == {}


def test_serperdev_empty_input(sf):

    result = sf.serperdev(
        [],
        serperdevApi="fake_api"
    )

    assert result == {}


# TEST FILTER DECORATOR

@patch.object(search_and_filter, "_load_credibility_scores")
def test_filter_returns_top_3(mock_scores, sf):

    mock_scores.return_value = {
        "BBC": 99,
        "Reuters": 98,
        "CNN": 85,
        "Fox": 70
    }

    fake_output = {
        "1": {"name": "BBC", "url": "a"},
        "2": {"name": "Reuters", "url": "b"},
        "3": {"name": "CNN", "url": "c"},
        "4": {"name": "Fox", "url": "d"},
    }

    decorated = search_and_filter._filter(
        lambda self: fake_output
    )

    result = decorated(sf)

    assert len(result) == 3
    assert "1" in result
    assert "2" in result
    assert "3" in result
    assert "4" not in result


class TestFallbackLogic:

    @patch("backend.search_handler.requests.get")
    @patch.object(search_and_filter, "_load_credibility_scores")
    def test_gnews_fallback_hits_429(
        self,
        mock_scores,
        mock_get
    ):

        sf = search_and_filter()

        mock_scores.return_value = {}

        # First response:
        # 200 OK but zero articles
        first_response = Mock()
        first_response.status_code = 200
        first_response.json.return_value = {
            "articles": []
        }

        # Second response:
        # Rate limit error
        second_response = Mock()
        second_response.status_code = 429

        # Sequential responses
        mock_get.side_effect = [
            first_response,
            second_response
        ]

        # Simulate backend logic
        gnews_specific = "specific query"
        gnews_broad = "broad query"

        search_results = sf.gnews([gnews_specific])

        if not search_results:
            search_results = sf.gnews([gnews_broad])

        # Final result should still be empty
        assert search_results == {}

        # Verify API called twice
        assert mock_get.call_count == 2