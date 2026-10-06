from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthenticatedUserResponse(BaseModel):
    id: int
    email: str
    employee_id: int | None
    permissions: list[str]