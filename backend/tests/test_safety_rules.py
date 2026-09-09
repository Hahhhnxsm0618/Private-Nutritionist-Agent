from app.safety.output import OutputSafetyChecker
from app.safety.rules import RiskLevel, SafetyRuleEngine


def test_emergency_message_is_high_risk_with_fixed_reply() -> None:
    decision = SafetyRuleEngine().evaluate("我现在胸痛并且呼吸困难怎么办？")

    assert decision.risk_level is RiskLevel.HIGH
    assert decision.action == "fixed_reply"
    assert decision.fixed_response
    assert "就医" in decision.fixed_response


def test_medication_dosage_message_is_medium_risk() -> None:
    decision = SafetyRuleEngine().evaluate("降压药一天应该吃几片？")

    assert decision.risk_level is RiskLevel.MEDIUM
    assert decision.action == "fixed_reply"
    assert "专业" in decision.fixed_response


def test_general_food_question_is_low_risk_and_can_reach_agent() -> None:
    decision = SafetyRuleEngine().evaluate("番茄和鸡蛋可以一起吃吗？")

    assert decision.risk_level is RiskLevel.LOW
    assert decision.action == "allow"
    assert decision.fixed_response is None


def test_output_checker_blocks_diagnosis_and_medication_instructions() -> None:
    result = OutputSafetyChecker().check("你患有糖尿病，应该把药量增加到两片。")

    assert result.allowed is False
    assert result.reason in {"diagnosis", "medication_instruction"}


def test_output_checker_blocks_confirmed_allergy_conflict() -> None:
    result = OutputSafetyChecker().check("可以放心吃花生。", allergies=["花生"])

    assert result.allowed is False
    assert result.reason == "allergy_conflict"
