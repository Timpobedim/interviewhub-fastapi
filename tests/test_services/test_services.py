from datetime import timedelta

import jwt as pyjwt
import pytest

from app.models.domain.users import User, UserInDB
from app.models.schemas.questions import normalize_tags
from app.services import jwt, security
from app.services.questions import get_slug_for_question


def test_creating_jwt_token_and_reading_username_back() -> None:
    token = jwt.create_access_token_for_user(User(username="tester", email="t@example.com"), "key")

    assert jwt.get_username_from_token(token, "key") == "tester"


def test_error_when_wrong_token_secret() -> None:
    token = jwt.create_access_token_for_user(User(username="tester", email="t@example.com"), "key")

    with pytest.raises(ValueError, match="decode"):
        jwt.get_username_from_token(token, "wrong-key")


def test_error_when_token_has_foreign_subject() -> None:
    token = pyjwt.encode({"username": "tester", "sub": "refresh", "exp": 4102444800}, "key")

    with pytest.raises(ValueError, match="subject"):
        jwt.get_username_from_token(token, "key")


def test_error_when_token_payload_is_malformed() -> None:
    token = jwt.create_jwt_token(
        jwt_content={"nickname": "tester"},
        secret_key="key",
        expires_delta=timedelta(minutes=1),
    )

    with pytest.raises(ValueError, match="malformed"):
        jwt.get_username_from_token(token, "key")


def test_password_hash_roundtrip_supports_long_passwords() -> None:
    long_password = "пароль-" * 30  # > 72 байт — bcrypt без предхеширования бы упал
    user = UserInDB(username="u", email="u@example.com")

    user.change_password(long_password)

    assert user.check_password(long_password)
    assert not user.check_password(long_password + "x")


def test_verify_password_returns_false_for_broken_hash() -> None:
    assert not security.verify_password("anything", "not-a-bcrypt-hash")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Что такое GIL?", "chto-takoe-gil"),
        ("Как работает JOIN в PostgreSQL", "kak-rabotaet-join-v-postgresql"),
    ],
)
def test_slug_is_transliterated(title: str, expected: str) -> None:
    assert get_slug_for_question(title) == expected


def test_slug_fallback_for_title_without_letters() -> None:
    assert get_slug_for_question("??? !!!").startswith("question-")


def test_tags_are_normalized() -> None:
    assert normalize_tags([" Python", "SQL", "python", "", "x" * 50]) == ["python", "sql", "x" * 40]
