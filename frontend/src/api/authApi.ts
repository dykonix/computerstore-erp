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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // Keep the status fallback when the server returns a non-JSON error.
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function fetchCurrentUser(accessToken: string): Promise<AuthenticatedUser> {
  return request<AuthenticatedUser>('/api/auth/me', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}