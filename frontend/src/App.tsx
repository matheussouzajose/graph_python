import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { GuestRoute } from '@/components/auth/GuestRoute'
import { AppShell } from '@/components/layout/AppShell'
import { HomePage } from '@/pages/HomePage'
import { OrdersPage } from '@/pages/OrdersPage'
import { ProductsPage } from '@/pages/ProductsPage'
import { ProductCatalogPage } from '@/pages/ProductCatalogPage'
import { CustomersPage } from '@/pages/CustomersPage'
import { RecommendationsPage } from '@/pages/RecommendationsPage'
import { OraclePage } from '@/pages/OraclePage'
import { AgentsPage } from '@/pages/AgentsPage'
import { LoginPage } from '@/pages/LoginPage'
import { SettingsPage } from '@/pages/SettingsPage'

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <GuestRoute>
            <LoginPage />
          </GuestRoute>
        }
      />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppShell>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/pedidos" element={<OrdersPage />} />
                <Route path="/produtos" element={<ProductsPage />} />
                <Route path="/catalogo-produtos" element={<ProductCatalogPage />} />
                <Route path="/clientes" element={<CustomersPage />} />
                <Route path="/recomendacoes" element={<RecommendationsPage />} />
                <Route path="/oraculo" element={<OraclePage />} />
                <Route path="/agentes" element={<AgentsPage />} />
                <Route path="/configuracoes" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/login" replace />} />
              </Routes>
            </AppShell>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
