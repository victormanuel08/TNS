export const useAuthState = () => {
  const accessToken = useState<string | null>(
    'auth-access-token',
    () => null
  )
  const refreshToken = useState<string | null>(
    'auth-refresh-token',
    () => null
  )
  const apiKey = useState<string | null>('auth-api-key', () => null)

  return {
    accessToken,
    refreshToken,
    apiKey
  }
}
