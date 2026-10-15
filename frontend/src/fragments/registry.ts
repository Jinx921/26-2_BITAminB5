import type { FragmentComponent, FragmentType } from './types'

const registry = new Map<FragmentType, FragmentComponent>()
let fallback: FragmentComponent | null = null

/** type 별 컴포넌트를 등록한다. 같은 type 을 다시 등록하면 덮어쓴다 */
export function registerFragment<T>(type: FragmentType, component: FragmentComponent<T>) {
  registry.set(type, component as FragmentComponent)
}

export function registerFallback(component: FragmentComponent) {
  fallback = component
}

export function resolveFragment(type: FragmentType): FragmentComponent | null {
  return registry.get(type) ?? fallback
}

export function registeredTypes(): FragmentType[] {
  return [...registry.keys()]
}
