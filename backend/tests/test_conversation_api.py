
from fastapi.testclient import TestClient

from app.auth.router import get_current_user
from app.conversation.router import get_conversation_service
from app.conversation.service import ConversationService
from app.main import app


class FakeRepository:
    def __init__(self) -> None:
        self.conversations = {}
        self.messages = {}
        self.safety_events = []
        self.counter = 0

    async def create_conversation(self, user_id, title, now):
        self.counter += 1
        conversation = type("Conversation", (), {
            "id": f"conversation-{self.counter}",
            "user_id": user_id,
            "title": title,
            "status": "active",
            "last_active_at": now,
            "created_at": now,
            "updated_at": now,
        })()
        self.conversations[conversation.id] = conversation
        return conversation

    async def list_conversations(self, user_id, include_archived):
        return [
            conversation
            for conversation in self.conversations.values()
            if conversation.user_id == user_id
            and (include_archived or conversation.status != "archived")
        ]

    async def get_conversation(self, user_id, conversation_id):
        conversation = self.conversations.get(conversation_id)
        return conversation if conversation and conversation.user_id == user_id else None

    async def get_message(self, user_id, conversation_id, message_id):
        message = self.messages.get(message_id)
        return message if message and message.user_id == user_id and message.conversation_id == conversation_id else None

    async def list_messages_by_request_id(self, user_id, conversation_id, request_id):
        return [
            message
            for message in self.messages.values()
            if message.user_id == user_id
            and message.conversation_id == conversation_id
            and message.request_id == request_id
        ]

    async def archive_conversation(self, conversation, now):
        conversation.status = "archived"
        conversation.updated_at = now
        return conversation

    async def list_messages(self, user_id, conversation_id, limit):
        return [
            message
            for message in self.messages.values()
            if message.user_id == user_id and message.conversation_id == conversation_id
        ][:limit]

    async def create_message(self, user_id, conversation_id, role, content, status, request_id, now):
        self.counter += 1
        message = type("Message", (), {
            "id": f"message-{self.counter}",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "status": status,
            "risk_level": None,
            "request_id": request_id,
            "trace_id": None,
            "citations": None,
            "created_at": now,
        })()
        self.messages[message.id] = message
        return message

    async def update_message_content(self, message, content, status=None):
        message.content = content
        if status is not None:
            message.status = status
        return message

    async def update_message_status(self, message, status):
        message.status = status
        return message

    async def create_safety_event(
        self, user_id, conversation_id, message_id, decision, request_id, trace_id, now
    ):
        self.safety_events.append(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "decision": decision,
                "request_id": request_id,
                "trace_id": trace_id,
                "created_at": now,
            }
        )

    async def touch_conversation(self, conversation, now):
        conversation.last_active_at = now
        conversation.updated_at = now

    async def commit(self):
        return None


def test_conversation_and_message_api_persists_user_scoped_data() -> None:
    service = ConversationService(FakeRepository())
    current_user = {"id": "user-1"}
    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: type("User", (), current_user)()
    client = TestClient(app)

    try:
        created = client.post("/api/v1/conversations", json={"title": "早餐咨询"})
        assert created.status_code == 201
        conversation_id = created.json()["id"]

        listed = client.get("/api/v1/conversations")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        message = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers={"X-Request-ID": "request-123"},
            json={"content": "我早餐吃什么？"},
        )
        assert message.status_code == 201
        assert message.json()["user_message"]["role"] == "user"
        assert message.json()["user_message"]["status"] == "succeeded"
        assert message.json()["user_message"]["request_id"] == "request-123"
        assert message.json()["assistant_message"]["status"] == "succeeded"
        assert message.json()["safety"]["risk_level"] == "low"

        messages = client.get(f"/api/v1/conversations/{conversation_id}/messages")
        assert messages.status_code == 200
        assert messages.json()[0]["content"] == "我早餐吃什么？"

        archived = client.delete(f"/api/v1/conversations/{conversation_id}")
        assert archived.status_code == 204

        hidden = client.get("/api/v1/conversations")
        assert hidden.json() == []

        rejected = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"content": "继续"},
        )
        assert rejected.status_code == 409
        assert rejected.json()["detail"]["code"] == "CONVERSATION_ARCHIVED"

        retry = client.post(
            f"/api/v1/conversations/{conversation_id}/retry",
            params={"message_id": message.json()["user_message"]["id"]},
        )
        assert retry.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_conversation_api_hides_other_users_resources() -> None:
    repository = FakeRepository()
    service = ConversationService(repository)
    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": "user-1"})()
    client = TestClient(app)

    try:
        created = client.post("/api/v1/conversations", json={"title": "私密会话"})
        conversation_id = created.json()["id"]
        app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": "user-2"})()

        response = client.get(f"/api/v1/conversations/{conversation_id}")

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


def test_stream_message_endpoint_returns_sse_events() -> None:
    service = ConversationService(FakeRepository())
    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": "user-1"})()
    client = TestClient(app)

    try:
        created = client.post("/api/v1/conversations", json={})
        conversation_id = created.json()["id"]
        response = client.post(
            f"/api/v1/conversations/{conversation_id}/messages/stream",
            headers={"X-Request-ID": "stream-api-1"},
            json={"content": "给我一个早餐建议"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "event: delta" in response.text
        assert "event: done" in response.text
    finally:
        app.dependency_overrides.clear()
