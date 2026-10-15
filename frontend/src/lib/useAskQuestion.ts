import { useMutation } from '@tanstack/react-query'
import { useRef } from 'react'
import { api } from '@/api'
import type { QuestionRequest } from '@/types/api'
import type { Display } from '@/types/display'

/** 질문 전송. 이전 요청이 진행 중이면 취소하고 새 요청을 보낸다 */
export function useAskQuestion() {
  const controller = useRef<AbortController | null>(null)
  const mutation = useMutation<Display, unknown, QuestionRequest>({
    mutationFn: async (req) => {
      controller.current?.abort()
      const c = new AbortController()
      controller.current = c
      try {
        return await api.askQuestion(req, c.signal)
      } finally {
        if (controller.current === c) controller.current = null
      }
    },
  })
  return { ...mutation, cancel: () => controller.current?.abort() }
}
