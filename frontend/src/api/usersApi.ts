import { apiRequest } from './apiClient'

export interface UserRecord {
  id: number
  username: string
  email: string
  mobile: string
  employee_id: number | null
  employee_name: string | null
  is_active: boolean
  role_ids: number[]
  role_names: string[]
}

export interface EmployeeOption {
  id: number
  name: string | null
  email: string
}

export interface RoleOption {
  id: number
  name: string
}

export interface UserFormData {
  employees: EmployeeOption[]
  roles: RoleOption[]
}

export interface UserCreateRequest {
  username: string
  email: string
  mobile: string
  employee_id: number | null
  initial_password: string
}

export function listUsers(): Promise<UserRecord[]> {
  return apiRequest<UserRecord[]>('/api/users')
}

export function getUserFormData(): Promise<UserFormData> {
  return apiRequest<UserFormData>('/api/users/form-data')
}

export function createUser(payload: UserCreateRequest): Promise<UserRecord> {
  return apiRequest<UserRecord>('/api/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateUser(
  userId: number,
  payload: { email?: string; mobile?: string; employee_id?: number | null },
): Promise<UserRecord> {
  return apiRequest<UserRecord>(`/api/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function updateUserStatus(
  userId: number,
  isActive: boolean,
): Promise<UserRecord> {
  return apiRequest<UserRecord>(`/api/users/${userId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  })
}

export function assignRole(userId: number, roleId: number): Promise<void> {
  return apiRequest<void>(`/api/users/${userId}/roles/${roleId}`, {
    method: 'POST',
  })
}

export function removeRole(userId: number, roleId: number): Promise<void> {
  return apiRequest<void>(`/api/users/${userId}/roles/${roleId}`, {
    method: 'DELETE',
  })
}
