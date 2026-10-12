/** 큰 글씨 모드, 읽어주기(speechSynthesis), 음성 입력(Web Speech API) */
import { useCallback, useEffect, useRef, useState } from 'react'

const BIG_TEXT_KEY = 'bitamin.bigText'

export function useBigText(): [boolean, () => void] {
  const [on, setOn] = useState<boolean>(() => {
    try {
      return localStorage.getItem(BIG_TEXT_KEY) === '1'
    } catch {
      return false
    }
  })
  useEffect(() => {
    document.documentElement.classList.toggle('big-text', on)
    try {
      localStorage.setItem(BIG_TEXT_KEY, on ? '1' : '0')
    } catch {
      /* ignore */
    }
    return () => document.documentElement.classList.remove('big-text')
  }, [on])
  return [on, () => setOn((v) => !v)]
}

export const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window

export function useSpeak() {
  const [speaking, setSpeaking] = useState(false)
  const stop = useCallback(() => {
    if (!canSpeak) return
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }, [])
  const speak = useCallback(
    (text: string) => {
      if (!canSpeak || !text.trim()) return
      window.speechSynthesis.cancel()
      const u = new SpeechSynthesisUtterance(text)
      u.lang = 'ko-KR'
      u.rate = 0.9
      u.onend = () => setSpeaking(false)
      u.onerror = () => setSpeaking(false)
      setSpeaking(true)
      window.speechSynthesis.speak(u)
    },
    [],
  )
  useEffect(() => stop, [stop])
  return { speak, stop, speaking, supported: canSpeak }
}

// Web Speech API 타입 (브라우저마다 접두어가 다르다)
interface SpeechRecognitionLike extends EventTarget {
  lang: string
  interimResults: boolean
  continuous: boolean
  start(): void
  stop(): void
  abort(): void
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null
  onend: (() => void) | null
  onerror: ((e: { error: string }) => void) | null
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === 'undefined') return null
  const w = window as unknown as { SpeechRecognition?: SpeechRecognitionCtor; webkitSpeechRecognition?: SpeechRecognitionCtor }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

export function useSpeechInput(onResult: (text: string) => void) {
  const ctor = getRecognitionCtor()
  const recRef = useRef<SpeechRecognitionLike | null>(null)
  const [listening, setListening] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const stop = useCallback(() => {
    recRef.current?.stop()
    setListening(false)
  }, [])

  const start = useCallback(() => {
    if (!ctor) return
    setError(null)
    const rec = new ctor()
    rec.lang = 'ko-KR'
    rec.interimResults = false
    rec.continuous = false
    rec.onresult = (e) => {
      const text = Array.from({ length: e.results.length }, (_, i) => e.results[i][0]?.transcript ?? '').join(' ').trim()
      if (text) onResult(text)
    }
    rec.onend = () => setListening(false)
    rec.onerror = (e) => {
      setListening(false)
      setError(e.error === 'not-allowed' ? '마이크 사용이 허용되지 않았어요.' : '음성을 알아듣지 못했어요. 다시 말해 주세요.')
    }
    recRef.current = rec
    setListening(true)
    rec.start()
  }, [ctor, onResult])

  useEffect(() => () => recRef.current?.abort(), [])
  return { supported: ctor !== null, listening, start, stop, error }
}
