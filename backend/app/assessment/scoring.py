"""无模型依赖的问卷确定性评分。"""

from typing import Literal

from pydantic import BaseModel, Field

DIMENSION_WEIGHTS = {
    "diet_structure": 0.40,
    "diet_behavior": 0.20,
    "activity_routine": 0.20,
    "goal_feasibility": 0.20,
}


class AssessmentQuestionForScoring(BaseModel):
    code: str
    dimension: Literal[
        "diet_structure", "diet_behavior", "activity_routine", "goal_feasibility"
    ]
    score_by_option: dict[str, int] = Field(default_factory=dict)


class AssessmentAnswerForScoring(BaseModel):
    question_code: str
    value: str | None = None
    status: Literal["answered", "skipped", "not_applicable"] = "answered"


class AssessmentScoreResult(BaseModel):
    coverage: float
    baseline_score: float | None
    dimensions: dict[str, float | None]
    evidence: list[dict[str, str]]
    rule_version: str


def calculate_assessment_result(
    questions: list[AssessmentQuestionForScoring],
    answers: list[AssessmentAnswerForScoring],
    *,
    rule_version: str,
    minimum_score_coverage: float = 60.0,
) -> AssessmentScoreResult:
    question_by_code = {question.code: question for question in questions}
    answer_by_code = {answer.question_code: answer for answer in answers}
    applicable_count = len(questions)
    scored_answers: dict[str, tuple[AssessmentQuestionForScoring, int]] = {}
    for code, answer in answer_by_code.items():
        question = question_by_code.get(code)
        if question is None:
            raise ValueError(f"unknown question: {code}")
        if answer.status != "answered":
            continue
        if answer.value not in question.score_by_option:
            raise ValueError(f"invalid option for question: {code}")
        scored_answers[code] = (question, question.score_by_option[answer.value])

    coverage = round(len(scored_answers) / applicable_count * 100, 2) if applicable_count else 0.0
    dimensions: dict[str, float | None] = {}
    evidence: list[dict[str, str]] = []
    for dimension in DIMENSION_WEIGHTS:
        dimension_items = [
            (question, score)
            for question, score in scored_answers.values()
            if question.dimension == dimension
        ]
        if not dimension_items:
            dimensions[dimension] = None
            continue
        dimensions[dimension] = round(
            sum(score for _, score in dimension_items)
            / sum(max(question.score_by_option.values()) for question, _ in dimension_items)
            * 100,
            2,
        )
        evidence.extend(
            {"question_code": question.code, "option": answer_by_code[question.code].value or ""}
            for question, _ in dimension_items
        )

    baseline_score = None
    if coverage >= minimum_score_coverage:
        available_weights = sum(
            DIMENSION_WEIGHTS[dimension]
            for dimension, score in dimensions.items()
            if score is not None
        )
        baseline_score = round(
            sum((score or 0) * DIMENSION_WEIGHTS[dimension] for dimension, score in dimensions.items())
            / available_weights
            if available_weights
            else 0.0,
            2,
        )

    return AssessmentScoreResult(
        coverage=coverage,
        baseline_score=baseline_score,
        dimensions=dimensions,
        evidence=evidence,
        rule_version=rule_version,
    )
