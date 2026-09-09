from app.db.session import settings


def test_auth_settings_use_approved_token_lifetimes() -> None:
    assert settings.access_token_expire_minutes == 30
    assert settings.refresh_token_expire_days == 30
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_secret_key
