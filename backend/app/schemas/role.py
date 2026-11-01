from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PermissionScope = Literal["assigned_stores", "all_tenant_stores", "assigned_locations", "all_tenant_locations"]


class RoleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class RolePermissionGrantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permission_code: str = Field(min_length=1, max_length=120)
    scope: PermissionScope = "assigned_stores"


class RolePermissionReplaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permissions: list[RolePermissionGrantInput]


class RolePermissionResponse(BaseModel):
    permission_code: str
    description: str | None
    scope: PermissionScope


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    permissions: list[RolePermissionResponse]


class PermissionOption(BaseModel):
    code: str
    description: str | None


class RoleFormDataResponse(BaseModel):
    permissions: list[PermissionOption]
    can_manage_permissions: bool
