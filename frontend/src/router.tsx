import { createBrowserRouter } from 'react-router-dom'
import { Layout } from './components/Layout'
import { DashboardPage } from './pages/DashboardPage'
import { TendersPage } from './pages/TendersPage'
import { SitesPage } from './pages/SitesPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { SettingsPage } from './pages/SettingsPage'
import { LoginPage } from './pages/LoginPage'

// URL -> page mapping. The Layout wraps the authenticated pages (nav + shell);
// /login stands alone. We wire these to real data as each backend phase lands.
export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'tenders', element: <TendersPage /> },
      { path: 'sites', element: <SitesPage /> },
      { path: 'notifications', element: <NotificationsPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
])
