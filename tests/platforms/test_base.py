from writer_profile.platforms.base import ValidationResult


def test_validation_result_ok_truthy():
    assert bool(ValidationResult.ok()) is True


def test_validation_result_failure_has_issues():
    res = ValidationResult.fail(["too long by 10 chars", "hashtag forbidden"])
    assert bool(res) is False
    assert len(res.issues) == 2
    assert "too long" in res.issues[0]
