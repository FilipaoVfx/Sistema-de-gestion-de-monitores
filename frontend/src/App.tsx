import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider } from './components/ui/Toast'
import AppLayout from './components/layout/AppLayout'
import LoginPage              from './pages/LoginPage'
import DashboardPage          from './pages/DashboardPage'
import SalasPage              from './pages/SalasPage'
import MonitoresPage          from './pages/MonitoresPage'
import HorariosPage           from './pages/HorariosPage'
import AsignacionesPage       from './pages/AsignacionesPage'
import SolicitudesCambioPage  from './pages/SolicitudesCambioPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-bgPage">
      <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  )
  return user ? <>{children}</> : <Navigate to="/usuarios/login" replace />
}

/** Solo permite rol admin. Si un monitor entra por URL directa, redirige a `/`. */
function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  if (user?.rol !== 'admin') return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            {/* Login replica la ruta del backend Django (/usuarios/login/) */}
            <Route path="/usuarios/login"    element={<LoginPage />} />
            <Route path="/login"             element={<Navigate to="/usuarios/login" replace />} />

            <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route index                   element={<DashboardPage />} />
              {/* Solo admin: gestion de salas, monitores y horarios */}
              <Route path="/salas"           element={<AdminRoute><SalasPage /></AdminRoute>}            />
              <Route path="/salas/crear"     element={<AdminRoute><SalasPage /></AdminRoute>}            />
              <Route path="/monitores"       element={<AdminRoute><MonitoresPage /></AdminRoute>}        />
              <Route path="/monitores/crear" element={<AdminRoute><MonitoresPage /></AdminRoute>}        />
              <Route path="/horarios"        element={<AdminRoute><HorariosPage /></AdminRoute>}         />
              <Route path="/horarios/crear"  element={<AdminRoute><HorariosPage /></AdminRoute>}         />
              {/* Compartidas: ambos roles pero con vista filtrada por permisos en el componente */}
              <Route path="/asignaciones"       element={<AsignacionesPage />} />
              <Route path="/asignaciones/crear" element={<AsignacionesPage />} />
              <Route path="/solicitudes-cambio" element={<SolicitudesCambioPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  )
}
