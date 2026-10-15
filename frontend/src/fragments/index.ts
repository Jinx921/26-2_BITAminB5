import { registerFallback, registerFragment } from './registry'
import { CautionFragment } from './components/CautionFragment'
import { ChartFragment } from './components/ChartFragment'
import { ConfidenceFragment } from './components/ConfidenceFragment'
import { DetailsFragment } from './components/DetailsFragment'
import { DocumentFragment } from './components/DocumentFragment'
import { HeadlineFragment } from './components/HeadlineFragment'
import { MapFragment } from './components/MapFragment'
import { UnknownFragment } from './components/UnknownFragment'

// 기본 조각 등록. 새 조각 종류가 생기면 여기서 registerFragment 로 추가한다
registerFragment('headline', HeadlineFragment)
registerFragment('details', DetailsFragment)
registerFragment('caution', CautionFragment)
registerFragment('confidence', ConfidenceFragment)
registerFragment('map', MapFragment)
registerFragment('chart', ChartFragment)
registerFragment('document', DocumentFragment)
registerFragment('unknown', UnknownFragment)
registerFallback(UnknownFragment)

export { FragmentRenderer } from './FragmentRenderer'
export { toFragments, FRAGMENT_ORDER } from './toFragments'
export { registerFragment, resolveFragment, registeredTypes } from './registry'
export type { FragmentContext, FragmentProps, Mode } from './types'
