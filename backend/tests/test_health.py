from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_service_status() -> None:
    """健康检查应返回稳定的机器可读响应。"""
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "nutrition-agent-api",
    }
