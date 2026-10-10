import { apiRequest } from './apiClient'

export interface AuthenticatedUser {
  id: number
  email: string
  employee_id: number | null
  permissions: string[]
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
}

export function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function fetchCurrentUser(
  accessToken: string,
): Promise<AuthenticatedUser> {
  return apiRequest<AuthenticatedUser>('/api/auth/me', {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })
}