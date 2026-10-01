import base64
import hashlib

import bcrypt


def generate_salt() -> str:
    return bcrypt.gensalt().decode()


def _prehash(password: str) -> bytes:
    """Сворачивает пароль в SHA-256 перед bcrypt.

    bcrypt учитывает только первые 72 байта, а bcrypt ≥ 5.0 бросает ошибку на более длинном
    вводе. Со схемой «соль + пароль» лимит легко превысить, поэтому пароль с солью
    сначала хешируется в SHA-256 — это 44 байта base64 при любой исходной длине.
    """
    return base64.b64encode(hashlib.sha256(password.encode()).digest())


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(plain_password), hashed_password.encode())
    except ValueError:
        return False
