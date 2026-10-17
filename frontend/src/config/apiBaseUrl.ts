const loopbackHosts = new Set(['localhost', '127.0.0.1', '[::1]'])

export function validateVercelApiBaseUrl(
  apiBaseUrl: string | undefined,
  isVercelBuild: boolean,
): void {
  if (!isVercelBuild) return

  let apiUrl: URL
  try {
    apiUrl = new URL(apiBaseUrl ?? '')
  } catch {
    throw new Error(
      'Vercel 배포에는 VITE_API_BASE_URL에 실제 백엔드 HTTPS 주소를 설정해야 합니다.',
    )
  }
  if (apiUrl.protocol !== 'https:' || loopbackHosts.has(apiUrl.hostname)) {
    throw new Error(
      'Vercel 배포의 VITE_API_BASE_URL은 localhost가 아닌 HTTPS 백엔드 주소여야 합니다.',
    )
  }
}
