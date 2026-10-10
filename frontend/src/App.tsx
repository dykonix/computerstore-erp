import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
} from 'react-router-dom'
import './App.css'

import Sales from './pages/Sales'
import ProductMaster from './pages/ProductMaster'
import Inventory from './pages/Inventory'
import SupplierMaster from './pages/SupplierMaster'
import CategoryMaster from './pages/CategoryMaster'
import WarrantyMaster from './pages/WarrantyMaster'
import PromotionMaster from './pages/PromotionMaster'

import { AuthProvider } from './auth/AuthProvider'
import { useAuth } from './auth/useAuth'
import LoginForm from './components/LoginForm'

const navigationItems: {
  label: string
  path: string
  permission?: string
}[] = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Products', path: '/products' },
  { label: 'Categories', path: '/categories' },
  { label: 'Warranties', path: '/warranties' },
  { label: 'Promotions', path: '/promotions' },
  { label: 'Inventory', path: '/inventory' },
  { label: 'Customers', path: '/customers' },
  { label: 'Suppliers', path: '/suppliers' },
  { label: 'Sales', path: '/sales', permission: 'sell' },
  { label: 'Stores', path: '/stores' },
  { label: 'Employees', path: '/employees' },
  { label: 'Users', path: '/users', permission: 'users.manage' },
  { label: 'Roles', path: '/roles', permission: 'roles.manage' },
  { label: 'Reports', path: '/reports', permission: 'reports.view' },
]

function Header() {
  const { user, logout } = useAuth()

  return (
    <header className="app-header">
      <p className="app-name">Mahamaya Computers</p>

      {user && (
        <div className="account-menu">
          <span>{user.email}</span>

          <button type="button" onClick={logout}>
            Sign out
          </button>
        </div>
      )}
    </header>
  )
}

function Navigation() {
  const { user, hasPermission } = useAuth()

  if (!user) {
    return null
  }

  return (
    <nav className="main-navigation" aria-label="Main navigation">
      <ul>
        {navigationItems.map(({ label, path, permission }) => (
          <li key={path}>
            {permission && !hasPermission(permission) ? (
              <span
                className="navigation-disabled"
                aria-disabled="true"
                title="You do not have access to this section"
              >
                {label}
              </span>
            ) : (
              <NavLink to={path}>{label}</NavLink>
            )}
          </li>
        ))}
      </ul>
    </nav>
  )
}

function MainContent() {
  const { user, loading, hasPermission } = useAuth()

  if (loading) {
    return (
      <main className="main-content">
        <div className="loading-panel">
          Checking your access...
        </div>
      </main>
    )
  }

  if (!user) {
    return (
      <main className="main-content login-content">
        <LoginForm />
      </main>
    )
  }

  const restrictedElement = (
    permission: string,
    title: string,
  ) =>
    hasPermission(permission) ? (
      <PageHeading title={title} />
    ) : (
      <Navigate to="/dashboard" replace />
    )

  return (
    <main className="main-content">
      <Routes>
        <Route
          path="/"
          element={<Navigate to="/dashboard" replace />}
        />

        {navigationItems.map(({ label, path, ...item }) => (
          <Route
            key={path}
            path={path}
            element={
              path === '/products' ? (
                <ProductMaster />
              ) : path === '/inventory' ? (
                <Inventory />
              ) : path === '/categories' ? (
                <CategoryMaster />
              ) : path === '/warranties' ? (
                <WarrantyMaster />
              ) : path === '/promotions' ? (
                <PromotionMaster />
              ) : path === '/suppliers' ? (
                <SupplierMaster />
              ) : path === '/sales' ? (
                <Sales />
              ) : item.permission ? (
                restrictedElement(item.permission, label)
              ) : (
                <PageHeading title={label} />
              )
            }
          />
        ))}

        <Route
          path="*"
          element={<Navigate to="/dashboard" replace />}
        />
      </Routes>
    </main>
  )
}

function PageHeading({ title }: { title: string }) {
  return <h1>{title}</h1>
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="app-shell">
          <Header />
          <Navigation />
          <MainContent />
        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App