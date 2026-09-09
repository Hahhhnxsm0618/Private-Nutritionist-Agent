"""对模型或规则生成的回答执行后置安全检查。"""

from pydantic import BaseModel


class OutputSafetyResult(BaseModel):
    allowed: bool
    reason: str | None = None


class OutputSafetyChecker:
    def check(
        self,
        text: str,
        *,
        allergies: list[str] | None = None,
        avoidances: list[str] | None = None,
    ) -> OutputSafetyResult:
        if "诊断为" in text or "你患有" in text or "确诊为" in text:
            return OutputSafetyResult(allowed=False, reason="diagnosis")
        medication_terms = ("增加药量", "减少药量", "停药", "换药", "每天吃几片")
        if any(term in text for term in medication_terms):
            return OutputSafetyResult(allowed=False, reason="medication_instruction")
        for item in allergies or []:
            if item and item in text:
                return OutputSafetyResult(allowed=False, reason="allergy_conflict")
        for item in avoidances or []:
            if item and item in text:
                return OutputSafetyResult(allowed=False, reason="avoidance_conflict")
        return OutputSafetyResult(allowed=True)
