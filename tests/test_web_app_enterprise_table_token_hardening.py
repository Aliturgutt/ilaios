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
