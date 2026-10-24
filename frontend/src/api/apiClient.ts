const TOKEN_KEY = 'computerstore_access_token'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
export async function apiRequest<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const accessToken = window.localStorage.getItem(TOKEN_KEY)

  const headers = new Headers(options?.headers)
  headers.set('Content-Type', 'application/json')

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`

    try {
      const payload = (await response.json()) as {
        detail?: string | Array<{ msg?: string }>
      }

      if (typeof payload.detail === 'string') {
        detail = payload.detail
      }

      if (Array.isArray(payload.detail)) {
        detail = payload.detail
          .map((item) => item.msg ?? 'Invalid value')
          .join(', ')
      }
    } catch {
      // Keep the status fallback when the server returns a non-JSON error.
    }

    throw new Error(detail)
  }

  return response.json() as Promise<T>
}
