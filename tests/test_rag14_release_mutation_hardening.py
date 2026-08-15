from pathlib import Path


WORKFLOW = Path(".github/workflows/aws-r01-image-publish.yml")


def test_r01_image_publish_requires_explicit_exact_release_dispatch() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "\n  push:" not in text
    assert "source_sha:" in text
    assert "confirm_external_mutation:" in text
    assert "inputs.confirm_external_mutation == true" in text
    assert "SOURCE_SHA: ${{ inputs.source_sha }}" in text
    assert "ref: ${{ inputs.source_sha }}" in text
    assert "persist-credentials: false" in text
    assert "r01-${SOURCE_SHA}" in text


def test_r01_image_publish_uses_immutable_action_revisions() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert (
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262" in text
    )
    assert (
        "aws-actions/configure-aws-credentials@"
        "7474bc4690e29a8392af63c5b98e7449536d5c3a" in text
    )
    assert "uses: actions/checkout@v4" not in text
    assert "uses: aws-actions/configure-aws-credentials@v4" not in text
