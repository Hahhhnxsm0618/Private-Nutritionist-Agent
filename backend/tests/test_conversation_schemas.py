import pytest
from pydantic import ValidationError

from app.conversation.schemas import ConversationCreate, MessageCreate


def test_conversation_title_is_trimmed() -> None:
    request = ConversationCreate(title="  早餐咨询  ")

    assert request.title == "早餐咨询"


def test_message_content_cannot_be_blank() -> None:
    with pytest.raises(ValidationError):
        MessageCreate(content="   ")
