from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from flask import Flask

from app.auth import decorators
from app.auth.decorators import auth_required
from app.auth.jwt import create_access_token, decode_access_token
from app.schemas.auth import validate_login, validate_password_change, validate_registration


@pytest.fixture
def auth_app():
    app = Flask(__name__)
    app.config.update(JWT_SECRET_KEY="jwt-test-secret", JWT_ACCESS_TOKEN_EXPIRES_MINUTES=60)
    return app


def test_registration_validation_rejects_missing_and_invalid_fields():
    errors = validate_registration({"username": "x", "email": "bad", "password": "short"})
    assert {"username", "email", "password"} <= errors.keys()


def test_registration_validation_accepts_valid_payload():
    assert not validate_registration(
        {"username": "test_user", "email": "user@example.com", "password": "password123"}
    )


def test_login_validation_requires_identifier_and_password():
    assert validate_login({}) == {"identifier": "Identifier is required", "password": "Password is required"}


def test_password_change_validation_rejects_weak_password():
    assert "new_password" in validate_password_change(
        {"current_password": "password123", "new_password": "short"}
    )


def test_jwt_round_trip(auth_app):
    user_id = uuid4()
    with auth_app.app_context():
        token = create_access_token(user_id)
        assert decode_access_token(token) == user_id
        claims = jwt.decode(token, "jwt-test-secret", algorithms=["HS256"])
    assert set(claims) == {"sub", "iat", "exp"}


def test_jwt_rejects_expired_token(auth_app):
    token = jwt.encode(
        {"sub": str(uuid4()), "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        "jwt-test-secret",
        algorithm="HS256",
    )
    with auth_app.app_context():
        with pytest.raises(ValueError):
            decode_access_token(token)


def test_protected_route_rejects_missing_token(auth_app):
    @auth_app.get("/protected")
    @auth_required
    def protected():
        return {"ok": True}

    assert auth_app.test_client().get("/protected").status_code == 401


def test_protected_route_accepts_valid_active_user(auth_app, monkeypatch):
    user = SimpleNamespace(id=uuid4(), is_active=True, status="active")
    monkeypatch.setattr(decorators, "get_by_id", lambda user_id: user)
    with auth_app.app_context():
        token = create_access_token(user.id)

    @auth_app.get("/protected")
    @auth_required
    def protected():
        return {"user_id": str(decorators.g.current_user.id)}

    response = auth_app.test_client().get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json["user_id"] == str(user.id)
