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
import Users from './pages/Users'
import Roles from './pages/Roles'

import { AuthProvider } from './auth/AuthProvider'
import { useAuth } from './auth/useAuth'
import LoginForm from './components/LoginForm'

const navigationItems: {
  label: string
  path: string
  permissions?: string[]
}[] = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Products', path: '/products', permissions: ['products.manage'] },
  { label: 'Categories', path: '/categories', permissions: ['categories.manage'] },
  { label: 'Warranties', path: '/warranties', permissions: ['products.manage'] },
  { label: 'Promotions', path: '/promotions', permissions: ['offers.manage'] },
  { label: 'Inventory', path: '/inventory', permissions: ['inventory.view', 'inventory.manage'] },
  { label: 'Customers', path: '/customers', permissions: ['customers.manage'] },
  { label: 'Suppliers', path: '/suppliers', permissions: ['suppliers.manage'] },
  { label: 'Sales', path: '/sales', permissions: ['sell'] },
  { label: 'Stores', path: '/stores', permissions: ['stores.manage'] },
  { label: 'Employees', path: '/employees', permissions: ['employees.manage'] },
  { label: 'Users', path: '/users', permissions: ['users.manage'] },
  { label: 'Roles', path: '/roles', permissions: ['roles.manage'] },
  { label: 'Reports', path: '/reports', permissions: ['reports.view'] },
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
        {navigationItems
          .filter(({ permissions }) => !permissions || permissions.some(hasPermission))
          .map(({ label, path }) => (
            <li key={path}>
              <NavLink to={path}>{label}</NavLink>
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

  return (
    <main className="main-content">
      <Routes>
        <Route
          path="/"
          element={<Navigate to="/dashboard" replace />}
        />

        {navigationItems.map(({ label, path, permissions }) => {
          const page =
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
            ) : path === '/users' ? (
              <Users />
            ) : path === '/roles' ? (
              <Roles />
            ) : (
              <PageHeading title={label} />
            )

          const canAccess = !permissions || permissions.some(hasPermission)

          return (
            <Route
              key={path}
              path={path}
              element={canAccess ? page : <Navigate to="/dashboard" replace />}
            />
          )
        })}

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