from app.models.certificate import (
    Certificate,
    GraduationCheck,
    GraduationResult,
    GraduationRule,
)
from app.services.graduation import build_certificate, generate_certificate_number


def test_graduation_rule_contract():
    rule = GraduationRule(
        track_id=7,
        code="FINAL_PROJECT",
        name="Final Project",
        rule_type="THRESHOLD",
        threshold=75,
        is_mandatory=True,
        ordering=4,
        is_active=True,
    )

    assert rule.track_id == 7
    assert rule.is_mandatory is True
    assert rule.threshold == 75
    assert rule.ordering == 4


def test_graduation_result_and_check_relationship_contract():
    result = GraduationResult(
        student_id=11,
        track_id=7,
        overall_score=82,
        status="GRADUATED",
        eligible=True,
    )
    check = GraduationCheck(
        result=result,
        rule=GraduationRule(
            track_id=7,
            code="FINAL_PROJECT",
            name="Final Project",
            rule_type="THRESHOLD",
            threshold=75,
        ),
        passed=True,
        score=82,
    )

    assert check.result is result
    assert check.passed is True
    assert check.score == 82


def test_certificate_number_is_unique_format():
    number = generate_certificate_number()

    assert number.startswith("KODRAQ-")
    assert len(number) >= 20


def test_build_certificate_requires_graduated_result():
    result = GraduationResult(
        id=9,
        student_id=11,
        track_id=7,
        overall_score=82,
        status="GRADUATED",
        eligible=True,
    )

    certificate = build_certificate(
        result,
        certificate_number="KODRAQ-2026-TEST000001",
    )

    assert isinstance(certificate, Certificate)
    assert certificate.student_id == 11
    assert certificate.track_id == 7
    assert certificate.graduation_result_id == 9
    assert certificate.final_score == 82
    assert certificate.status == "ISSUED"


def test_build_certificate_rejects_non_graduated_result():
    result = GraduationResult(
        id=10,
        student_id=11,
        track_id=7,
        overall_score=64,
        status="NOT_GRADUATED",
        eligible=False,
    )

    try:
        build_certificate(result)
    except ValueError as exc:
        assert "GRADUATED" in str(exc)
    else:
        raise AssertionError("Non-graduated result must not produce a certificate.")
