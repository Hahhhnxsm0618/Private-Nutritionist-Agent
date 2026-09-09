import pytest
from pydantic import ValidationError

from app.auth.schemas import LoginRequest, RegisterRequest


def test_auth_request_normalizes_email() -> None:
    request = RegisterRequest(email="  User@Example.COM ", password="Strong-password-123!")

    assert request.email == "user@example.com"


def test_auth_request_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="user@example.com", password="short")
