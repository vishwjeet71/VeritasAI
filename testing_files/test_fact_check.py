import pytest
from backend.fact_check_db import check_claim_in_db

class TestCheckClaimInDbInvalidInputs:

    @pytest.mark.parametrize(
        "search_queries",
        [
            None,
            "",
            "not_a_list",
            123,
            {},
            (),
            set(),
            [],
        ]
    )
    def test_invalid_search_queries_return_none(
        self,
        mocker,
        search_queries
    ):
        embedding_obj = mocker.Mock()

        result = check_claim_in_db(
            claim="some claim",
            searchQuerys=search_queries,
            embedding_obj=embedding_obj
        )

        assert result is None


class TestCheckClaimInDbInvalidInputs:

    @pytest.mark.parametrize(
        "search_queries",
        [
            None,
            "",
            "invalid",
            123,
            {},
            (),
            set(),
        ]
    )
    def test_non_list_search_queries_return_none(
        self,
        mocker,
        search_queries
    ):
        embedding_obj = mocker.Mock()

        result = check_claim_in_db(
            claim="claim",
            searchQuerys=search_queries,
            embedding_obj=embedding_obj
        )

        assert result is None

    def test_empty_search_queries_return_none(
        self,
        mocker
    ):
        embedding_obj = mocker.Mock()

        result = check_claim_in_db(
            claim="claim",
            searchQuerys=[],
            embedding_obj=embedding_obj
        )

        assert result is None