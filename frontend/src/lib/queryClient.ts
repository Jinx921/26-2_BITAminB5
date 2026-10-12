import { QueryClient } from '@tanstack/react-query'
import { isApiError } from '@/api/client'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // 4xx 는 다시 시도해도 같다. 네트워크·5xx 만 한 번 더
      retry: (count, err) => (isApiError(err) && err.status > 0 && err.status < 500 ? false : count < 1),
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
})
