"""问卷模板的营养师专业审核记录。"""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class AssessmentReview(UUIDPrimaryKeyMixin, Base):
    """保存结构化审核结论，不复制题库原文或用户健康文本。"""

    __tablename__ = "assessment_reviews"

    template_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_templates.id"), nullable=False, index=True
    )
    reviewer_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
