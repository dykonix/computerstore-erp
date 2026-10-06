import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt


class JWTConfigurationError(Exception):
    pass


class InvalidAccessTokenError(Exception):
    pass


_ALGORITHM_MINIMUM_SECRET_BYTES = {"HS256": 32, "HS384": 48, "HS512": 64}


@dataclass(frozen=True)
class JWTSettings:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


def get_jwt_settings() -> JWTSettings:
    secret_key = os.getenv("JWT_SECRET_KEY", "")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
    minimum_secret_bytes = _ALGORITHM_MINIMUM_SECRET_BYTES.get(algorithm)
    if minimum_secret_bytes is None:
        raise JWTConfigurationError("JWT_ALGORITHM must be HS256, HS384, or HS512")
    if len(secret_key.encode("utf-8")) < minimum_secret_bytes:
        raise JWTConfigurationError(
            f"JWT_SECRET_KEY must contain at least {minimum_secret_bytes} bytes"
        )

    try:
        expires_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    except ValueError as error:
        raise JWTConfigurationError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer"
        ) from error
    if expires_minutes <= 0:
        raise JWTConfigurationError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer"
        )

    return JWTSettings(secret_key, algorithm, expires_minutes)


def create_access_token(
    user_id: int, expires_delta: timedelta | None = None
) -> str:
    settings = get_jwt_settings()
    expires_at = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_access_token(token: str) -> int:
    settings = get_jwt_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require": ["sub", "exp"]},
        )
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.isdecimal():
            raise InvalidAccessTokenError("Invalid access token")
        user_id = int(subject)
        if user_id <= 0:
            raise InvalidAccessTokenError("Invalid access token")
        return user_id
    except jwt.PyJWTError as error:
        raise InvalidAccessTokenError("Invalid access token") from error