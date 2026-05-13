import pytest
from backend.input_handler import classify_input

# TEST 1: Valid URLs

class TestValidURLs:

    def test_standard_https_url(self):
        result = classify_input("https://www.thehindu.com/news/article123.html")
        assert result["type"] == "url"
        assert result["value"] == "https://www.thehindu.com/news/article123.html"

    def test_standard_http_url(self):
        result = classify_input("http://timesofindia.com/article/456")
        assert result["type"] == "url"
        assert result["value"] == "http://timesofindia.com/article/456"

    def test_url_with_query_params(self):
        result = classify_input("https://bbc.com/news?id=123&lang=en")
        assert result["type"] == "url"

    def test_url_with_subdomain(self):
        result = classify_input("https://sports.ndtv.com/cricket/india-wins-2024")
        assert result["type"] == "url"

    def test_url_with_path_and_slug(self):
        result = classify_input("https://indianexpress.com/article/india/chandrayaan-3-moon-landing-8890123/")
        assert result["type"] == "url"

    def test_url_with_fragment(self):
        result = classify_input("https://en.wikipedia.org/wiki/Chandrayaan-3#Landing")
        assert result["type"] == "url"

    def test_url_with_port(self):
        result = classify_input("https://example.com:8080/news/article")
        assert result["type"] == "url"

    def test_url_with_leading_whitespace(self):
        # System should strip and still classify correctly
        result = classify_input("  https://thehindu.com/article/123  ")
        assert result["type"] == "url"

    def test_short_valid_url(self):
        result = classify_input("https://bbc.co.uk")
        assert result["type"] == "url"


# TEST 2: Valid Queries

class TestValidQueries:

    def test_simple_factual_claim(self):
        result = classify_input("India landed on the moon in 2023")
        assert result["type"] == "query"
        assert result["value"] == "India landed on the moon in 2023"

    def test_question_format(self):
        result = classify_input("Was the moon landing faked?")
        assert result["type"] == "query"

    def test_multi_word_claim(self):
        result = classify_input("Elon Musk acquired Twitter in October 2022")
        assert result["type"] == "query"

    def test_claim_with_numbers(self):
        result = classify_input("India's population crossed 1.4 billion in 2023")
        assert result["type"] == "query"

    def test_claim_with_special_characters(self):
        result = classify_input("India's GDP grew by 7.2% in Q3 2023")
        assert result["type"] == "query"

    def test_long_query(self):
        long_query = (
            "The Indian government announced a new policy in 2023 that mandates "
            "all electric vehicles sold in India must be manufactured domestically "
            "with at least 50 percent local components by 2025"
        )
        result = classify_input(long_query)
        assert result["type"] == "query"

    def test_query_starting_with_www_but_no_scheme(self):
        # www.something.com without http/https is NOT a valid URL — treat as query
        result = classify_input("www.google.com is the most visited website")
        assert result["type"] == "query"

    def test_query_with_url_like_word_inside(self):
        # Contains the word "https" but is not a URL
        result = classify_input("The website https is a secure protocol used by websites")
        assert result["type"] == "query"

    def test_single_word_claim(self):
        result = classify_input("Chandrayaan")
        assert result["type"] == "query"

    def test_query_with_leading_whitespace(self):
        result = classify_input("  India is the most populous country  ")
        assert result["type"] == "query"
        assert result["value"] == "India is the most populous country"


# TEST 3: Edge Cases — Empty and Whitespace

class TestEmptyAndWhitespaceInput:

    def test_empty_string_raises_error(self):
        with pytest.raises(ValueError, match="empty"):
            classify_input("")

    def test_whitespace_only_raises_error(self):
        with pytest.raises(ValueError, match="empty"):
            classify_input("   ")

    def test_tab_only_raises_error(self):
        with pytest.raises(ValueError, match="empty"):
            classify_input("\t")

    def test_newline_only_raises_error(self):
        with pytest.raises(ValueError, match="empty"):
            classify_input("\n")

    def test_none_raises_type_error(self):
        with pytest.raises((TypeError, ValueError)):
            classify_input(None)


# TEST 4: Malformed URLs
class TestMalformedURLs:

    def test_http_with_no_domain(self):
        # "http://" with no netloc is malformed
        with pytest.raises(ValueError, match="invalid"):
            classify_input("http://")

    def test_https_with_no_domain(self):
        with pytest.raises(ValueError, match="invalid"):
            classify_input("https://")

    def test_url_with_spaces_in_domain(self):
        with pytest.raises(ValueError, match="invalid"):
            classify_input("https://the hindu.com/article")

    def test_url_missing_tld(self):
        # No TLD — debatable, but netloc exists so behavior depends on implementation
        # Document the actual behavior here
        result = classify_input("https://localhost/article")
        assert result["type"] in ("url", "query")  # accept either — just must not crash

    def test_ftp_scheme_is_not_valid(self):
        # System only accepts http/https — ftp should not be classified as url
        result = classify_input("ftp://files.example.com/data.csv")
        assert result["type"] == "query"  # treated as plain text, not a valid URL


# TEST 5: Output Structure Validation

class TestOutputStructure:

    def test_url_output_has_required_keys(self):
        result = classify_input("https://thehindu.com/article/123")
        assert "type" in result
        assert "value" in result

    def test_query_output_has_required_keys(self):
        result = classify_input("India won the 2011 cricket world cup")
        assert "type" in result
        assert "value" in result

    def test_url_type_value_is_string(self):
        result = classify_input("https://ndtv.com/news/article-123")
        assert isinstance(result["type"], str)
        assert isinstance(result["value"], str)

    def test_query_type_value_is_string(self):
        result = classify_input("Modi became PM in 2014")
        assert isinstance(result["type"], str)
        assert isinstance(result["value"], str)

    def test_type_field_only_valid_values(self):
        result = classify_input("https://bbc.com/news")
        assert result["type"] in ("url", "query")

    def test_url_value_preserved_exactly(self):
        url = "https://indianexpress.com/article/india/test-123/"
        result = classify_input(url)
        assert result["value"] == url


# TEST 6: Boundary and Stress Cases

class TestBoundaryCases:

    def test_very_long_query(self):
        long_text = "India " * 500
        result = classify_input(long_text.strip())
        assert result["type"] == "query"

    def test_very_long_url(self):
        long_url = "https://example.com/" + "a" * 2000
        result = classify_input(long_url)
        assert result["type"] == "url"

    def test_unicode_query(self):
        result = classify_input("भारत ने 2023 में चंद्रमा पर लैंडिंग की")
        assert result["type"] == "query"

    def test_numeric_only_input(self):
        result = classify_input("12345")
        assert result["type"] == "query"

    def test_url_with_unicode_domain(self):
        result = classify_input("https://भारत.com/news")
        assert result["type"] in ("url", "query")

    def test_returns_dict_not_none(self):
        result = classify_input("https://thehindu.com")
        assert result is not None

    def test_multiple_calls_same_input_consistent(self):
        input_str = "https://bbc.com/news/world"
        result1 = classify_input(input_str)
        result2 = classify_input(input_str)
        assert result1["type"] == result2["type"]
        assert result1["value"] == result2["value"]