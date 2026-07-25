import { Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { HomePage } from '@/pages/HomePage'
import { ProductsPage } from '@/pages/ProductsPage'
import { CustomersPage } from '@/pages/CustomersPage'
import { RecommendationsPage } from '@/pages/RecommendationsPage'
import { OraclePage } from '@/pages/OraclePage'

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/produtos" element={<ProductsPage />} />
        <Route path="/clientes" element={<CustomersPage />} />
        <Route path="/recomendacoes" element={<RecommendationsPage />} />
        <Route path="/oraculo" element={<OraclePage />} />
      </Routes>
    </AppShell>
  )
}
