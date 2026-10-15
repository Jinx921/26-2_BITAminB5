import { Component, type ReactNode } from 'react'

interface Props {
  name: string
  children: ReactNode
}
interface State {
  error: Error | null
}

/** 조각 하나가 깨져도 나머지 조각은 그대로 보이게 한다 */
export class FragmentBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error) {
    console.error(`[fragment:${this.props.name}]`, error)
  }

  render() {
    if (this.state.error) {
      return (
        <div role="alert" className="rounded-btn bg-canvas p-3 text-sm text-ink-3">
          이 부분({this.props.name})은 표시하지 못했습니다.
        </div>
      )
    }
    return this.props.children
  }
}
