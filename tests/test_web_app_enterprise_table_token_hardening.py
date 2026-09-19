from __future__ import annotations

import pytest

from services.web_app_enterprise_table_runtime import (
    WebAppEnterpriseTableError,
    WebAppEnterpriseTableRuntime,
)


def test_enterprise_table_tokens_reject_ambiguous_or_nonprintable_values() -> None:
    for token in (
        " id",
        "id ",
        "id\u200b",
        "status\u007f",
    ):
        with pytest.raises(WebAppEnterpriseTableError) as exc:
            WebAppEnterpriseTableRuntime._token(token, "column.key")

        assert exc.value.code == "INVALID_TOKEN"


def test_enterprise_table_search_rejects_nonprintable_text() -> None:
    for search in ("owner\u200b", "status\u007f"):
        with pytest.raises(WebAppEnterpriseTableError) as exc:
            WebAppEnterpriseTableRuntime._validate_query_inputs(
                filters=None,
                search=search,
            )

        assert exc.value.code == "INVALID_SEARCH"


def test_enterprise_table_filter_text_rejects_nonprintable_values() -> None:
    for value in ("owner\u200b", "status\u007f"):
        with pytest.raises(WebAppEnterpriseTableError) as exc:
            WebAppEnterpriseTableRuntime._validate_query_inputs(
                filters={"status": value},
                search=None,
            )

        assert exc.value.code == "INVALID_FILTER_VALUE"
