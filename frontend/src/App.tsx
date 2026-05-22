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
              <Route index                   element={<DashboardPage />}        />
              <Route path="/salas"           element={<SalasPage />}            />
              <Route path="/salas/crear"     element={<SalasPage />}            />
              <Route path="/monitores"       element={<MonitoresPage />}        />
              <Route path="/monitores/crear" element={<MonitoresPage />}        />
              <Route path="/horarios"        element={<HorariosPage />}         />
              <Route path="/horarios/crear"  element={<HorariosPage />}         />
              <Route path="/asignaciones"    element={<AsignacionesPage />}     />
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
