from backend.article_fetcher import _single_article, fetch_article
import pytest
from unittest.mock import patch

from backend.article_fetcher import (
    _single_article,
    fetch_article
)


# SUCCESS CASE

@pytest.mark.asyncio
@patch("backend.article_fetcher.trafilatura.extract")
@patch("backend.article_fetcher.trafilatura.fetch_url")
async def test_single_article_success(
    mock_fetch_url,
    mock_extract
):

    mock_fetch_url.return_value = "<html>dummy</html>"
    mock_extract.return_value = "article text"

    output, error = await _single_article(
        "https://example.com"
    )

    assert error is None
    assert output == "article text"


# NO HTML CASE

@pytest.mark.asyncio
@patch("backend.article_fetcher.trafilatura.fetch_url")
async def test_single_article_no_html(
    mock_fetch_url
):

    mock_fetch_url.return_value = None

    output, error = await _single_article(
        "https://example.com"
    )

    assert output is None
    assert error == (
        "no HTML returned "
        "(possible bot-block or empty page)"
    )


# NO TEXT CASE

@pytest.mark.asyncio
@patch("backend.article_fetcher.trafilatura.extract")
@patch("backend.article_fetcher.trafilatura.fetch_url")
async def test_single_article_no_text(
    mock_fetch_url,
    mock_extract
):

    mock_fetch_url.return_value = "<html></html>"
    mock_extract.return_value = None

    output, error = await _single_article(
        "https://example.com"
    )

    assert output is None
    assert error == (
        "HTML fetched but no text "
        "could be extracted"
    )


# EXCEPTION CASE

@pytest.mark.asyncio
@patch("backend.article_fetcher.trafilatura.fetch_url")
async def test_single_article_exception(
    mock_fetch_url
):

    mock_fetch_url.side_effect = Exception(
        "network failure"
    )

    output, error = await _single_article(
        "https://example.com"
    )

    assert output is None
    assert "network failure" in error


# BATCH FETCH TEST

@patch("backend.article_fetcher._fetch_article_wrapper")
def test_fetch_article(
    mock_wrapper
):

    mock_wrapper.return_value = (
        "article text",
        None
    )

    urls = [
        "https://a.com",
        "https://b.com"
    ]

    results = fetch_article(urls)

    assert len(results) == 2

    for output, error in results:
        assert output == "article text"
        assert error is None