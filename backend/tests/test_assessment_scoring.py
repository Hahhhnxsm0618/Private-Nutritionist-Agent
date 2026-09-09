import pytest

from app.assessment.scoring import (
    AssessmentAnswerForScoring,
    AssessmentQuestionForScoring,
    calculate_assessment_result,
)


def _questions() -> list[AssessmentQuestionForScoring]:
    return [
        AssessmentQuestionForScoring(
            code="food-variety",
            dimension="diet_structure",
            score_by_option={"often": 4, "sometimes": 2},
        ),
        AssessmentQuestionForScoring(
            code="meal-regularity",
            dimension="diet_behavior",
            score_by_option={"regular": 4, "sometimes": 2},
        ),
        AssessmentQuestionForScoring(
            code="sleep",
            dimension="activity_routine",
            score_by_option={"good": 4, "poor": 0},
        ),
        AssessmentQuestionForScoring(
            code="goal-fit",
            dimension="goal_feasibility",
            score_by_option={"ready": 4, "not_ready": 0},
        ),
    ]


def test_low_coverage_hides_baseline_score_but_returns_coverage() -> None:
    result = calculate_assessment_result(
        _questions(),
        [AssessmentAnswerForScoring(question_code="food-variety", value="often")],
        rule_version="assessment-rules-v1",
    )

    assert result.coverage == 25.0
    assert result.baseline_score is None
    assert result.rule_version == "assessment-rules-v1"


def test_score_uses_weighted_dimensions_and_skipped_answers_do_not_score_zero() -> None:
    result = calculate_assessment_result(
        _questions(),
        [
            AssessmentAnswerForScoring(question_code="food-variety", value="often"),
            AssessmentAnswerForScoring(question_code="meal-regularity", value="regular"),
            AssessmentAnswerForScoring(question_code="sleep", status="skipped"),
            AssessmentAnswerForScoring(question_code="goal-fit", value="ready"),
        ],
        rule_version="assessment-rules-v1",
    )

    assert result.coverage == 75.0
    assert result.baseline_score == pytest.approx(100.0)
    assert result.dimensions["diet_structure"] == 100.0
    assert result.dimensions["diet_behavior"] == 100.0
    assert result.dimensions["activity_routine"] is None
    assert result.dimensions["goal_feasibility"] == 100.0


def test_invalid_option_is_rejected_by_the_deterministic_rule() -> None:
    with pytest.raises(ValueError, match="invalid option"):
        calculate_assessment_result(
            _questions(),
            [AssessmentAnswerForScoring(question_code="food-variety", value="unknown")],
            rule_version="assessment-rules-v1",
        )
