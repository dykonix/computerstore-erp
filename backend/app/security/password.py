import secrets

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError


password_hash = PasswordHash.recommended()
_dummy_password_hash = password_hash.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return password_hash.verify(password, encoded_hash)
    except UnknownHashError:
        return False


def verify_dummy_password(password: str) -> None:
    verify_password(password, _dummy_password_hash)