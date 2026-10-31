/** In-memory bearer session; deliberately never persisted in browser storage. */
let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string): void {
  if (!token || token.length < 32 || /\s/.test(token)) {
    throw new Error('Invalid access token')
  }
  accessToken = token
}

export function clearAccessToken(): void {
  accessToken = null
}
