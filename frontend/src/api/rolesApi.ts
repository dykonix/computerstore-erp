import { apiRequest } from './apiClient'

export type PermissionScope = 'assigned_stores' | 'all_tenant_stores'

export interface RolePermissionGrant {
  permission_code: string
  description: string | null
  scope: PermissionScope
}

export interface RoleRecord {
  id: number
  name: string
  description: string | null
  is_active: boolean
  permissions: RolePermissionGrant[]
}

export interface PermissionOption {
  code: string
  description: string | null
}

export interface RoleFormData {
  permissions: PermissionOption[]
  can_manage_permissions: boolean
}

export interface RoleCreateRequest {
  name: string
  description: string | null
}

export function listRoles(): Promise<RoleRecord[]> {
  return apiRequest<RoleRecord[]>('/api/roles')
}

export function getRoleFormData(): Promise<RoleFormData> {
  return apiRequest<RoleFormData>('/api/roles/form-data')
}

export function createRole(payload: RoleCreateRequest): Promise<RoleRecord> {
  return apiRequest<RoleRecord>('/api/roles', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateRole(
  roleId: number,
  payload: { name?: string; description?: string | null; is_active?: boolean },
): Promise<RoleRecord> {
  return apiRequest<RoleRecord>(`/api/roles/${roleId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function replaceRolePermissions(
  roleId: number,
  permissions: Array<{ permission_code: string; scope: PermissionScope }>,
): Promise<RoleRecord> {
  return apiRequest<RoleRecord>(`/api/roles/${roleId}/permissions`, {
    method: 'PUT',
    body: JSON.stringify({ permissions }),
  })
}
