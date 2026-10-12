import { createBrowserRouter } from 'react-router-dom'
import { RequireRole } from '@/auth/RequireRole'
import { AdminLayout } from '@/layouts/AdminLayout'
import { CitizenLayout } from '@/layouts/CitizenLayout'
import { FieldLayout } from '@/layouts/FieldLayout'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { RoleRedirect } from '@/pages/RoleRedirect'
import { AdminFieldListPage } from '@/pages/admin/AdminFieldListPage'
import { AdminHomePage } from '@/pages/admin/AdminHomePage'
import { AdminRequestsPage } from '@/pages/admin/AdminRequestsPage'
import { CitizenHelpPage } from '@/pages/citizen/CitizenHelpPage'
import { CitizenHomePage } from '@/pages/citizen/CitizenHomePage'
import { CitizenPlacesPage } from '@/pages/citizen/CitizenPlacesPage'
import { CitizenSchedulePage } from '@/pages/citizen/CitizenSchedulePage'
import { FieldCellPage } from '@/pages/field/FieldCellPage'
import { FieldHomePage } from '@/pages/field/FieldHomePage'

/**
 * 역할별 라우트. 각 구역은 RequireRole 로 감싸 권한 없는 화면은 렌더링하지 않는다.
 *  /admin    관리자
 *  /citizen  시민 (모바일 우선)
 *  /field    현장 담당자 (관리자도 볼 수 있음)
 */
export const router = createBrowserRouter([
  { path: '/', element: <RoleRedirect /> },
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireRole roles={['admin']} />,
    children: [
      {
        path: '/admin',
        element: <AdminLayout />,
        children: [
          { index: true, element: <AdminHomePage /> },
          { path: 'requests', element: <AdminRequestsPage /> },
          { path: 'field-list', element: <AdminFieldListPage /> },
        ],
      },
    ],
  },
  {
    element: <RequireRole roles={['citizen']} />,
    children: [
      {
        path: '/citizen',
        element: <CitizenLayout />,
        children: [
          { index: true, element: <CitizenHomePage /> },
          { path: 'places', element: <CitizenPlacesPage /> },
          { path: 'schedule', element: <CitizenSchedulePage /> },
          { path: 'help/:facilityId', element: <CitizenHelpPage /> },
        ],
      },
    ],
  },
  {
    element: <RequireRole roles={['field_worker', 'admin']} />,
    children: [
      {
        path: '/field',
        element: <FieldLayout />,
        children: [
          { index: true, element: <FieldHomePage /> },
          { path: 'cells/:cellId', element: <FieldCellPage /> },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])
