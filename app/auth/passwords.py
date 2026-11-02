from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MIN_LENGTH = 12
COMMON = {
    "password1234",
    "123456789012",
    "qwertyuiop12",
    "passwordpassword",
    "administrator",
    "kissaten12345",
}

_hasher = PasswordHasher()
# 存在しないユーザーでも同程度の時間を使い、ユーザー存在有無を時間差で漏らさない
DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return _hasher.check_needs_rehash(stored_hash)


def validate_password(password: str, username: str = "") -> str | None:
    """問題があればエラーメッセージ、なければ None。"""
    if len(password) < MIN_LENGTH:
        return f"パスワードは{MIN_LENGTH}文字以上にしてください"
    if password.lower() in COMMON or (username and username.lower() in password.lower()):
        return "推測されやすいパスワードは使えません"
    if len(set(password)) < 5:
        return "もっと多様な文字を使ってください"
    return None
