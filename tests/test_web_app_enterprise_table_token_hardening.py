from __future__ import annotations

import pytest

from services.web_app_enterprise_table_runtime import (
    WebAppEnterpriseTableError,
    WebAppEnterpriseTableRuntime,
)


@pytest.mark.parametrize(
    "token",
    (
        " id",
        "id ",
        "id\u200b",
        "status\u007f",
    ),
)
def test_enterprise_table_tokens_reject_ambiguous_or_nonprintable_values(token: str) -> None:
    with pytest.raises(WebAppEnterpriseTableError) as exc:
        WebAppEnterpriseTableRuntime._token(token, "column.key")

    assert exc.value.code == "INVALID_TOKEN"
