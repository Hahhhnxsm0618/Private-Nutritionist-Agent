"""对用户消息执行前置风险识别。"""

from enum import Enum

from pydantic import BaseModel


class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SafetyDecision(BaseModel):
    risk_level: RiskLevel
    trigger_category: str
    action: str
    fixed_response: str | None
    rule_version: str = "safety-rules-v1"


HIGH_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("emergency_symptom", ("胸痛", "呼吸困难", "昏厥", "严重过敏", "喉咙肿")),
    ("special_population", ("孕妇", "怀孕", "哺乳期", "儿童", "小孩")),
    ("diagnosis_request", ("帮我诊断", "是不是糖尿病", "是不是高血压", "确诊")),
)

MEDIUM_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("medication_instruction", ("药物剂量", "药量", "吃几片", "停药", "换药", "调整药物")),
    ("chronic_condition", ("糖尿病怎么吃", "高血压怎么吃", "痛风怎么吃", "慢病饮食")),
    ("eating_disorder_risk", ("极端节食", "绝食", "催吐", "暴食")),
    ("drug_food_interaction", ("药物相互作用", "药和食物能一起")),
)

HIGH_RESPONSE = "这可能涉及需要及时处理的健康风险，我不能在线进行诊断或处理。请立即联系急救服务或尽快就医，并向医生说明具体症状。"
MEDIUM_RESPONSE = "这个问题可能涉及疾病或用药安全，我不能提供诊断、药物剂量或停药建议。请咨询医生或注册营养师，再根据专业意见调整饮食。"


class SafetyRuleEngine:
    """按固定优先级执行规则，高风险规则优先于中风险规则。"""

    def evaluate(self, text: str) -> SafetyDecision:
        for category, keywords in HIGH_RULES:
            if any(keyword in text for keyword in keywords):
                return SafetyDecision(
                    risk_level=RiskLevel.HIGH,
                    trigger_category=category,
                    action="fixed_reply",
                    fixed_response=HIGH_RESPONSE,
                )
        for category, keywords in MEDIUM_RULES:
            if any(keyword in text for keyword in keywords):
                return SafetyDecision(
                    risk_level=RiskLevel.MEDIUM,
                    trigger_category=category,
                    action="fixed_reply",
                    fixed_response=MEDIUM_RESPONSE,
                )
        return SafetyDecision(
            risk_level=RiskLevel.LOW,
            trigger_category="none",
            action="allow",
            fixed_response=None,
        )
