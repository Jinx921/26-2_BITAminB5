export function parseSuccessfulJson(text: string): unknown {
  if (!text) {
    throw new Error('서버가 비어 있는 응답을 반환했습니다.')
  }
  try {
    return JSON.parse(text)
  } catch {
    throw new Error('서버가 JSON이 아닌 응답을 반환했습니다.')
  }
}
