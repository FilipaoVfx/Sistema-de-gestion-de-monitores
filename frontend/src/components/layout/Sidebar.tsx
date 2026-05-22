import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Monitor, Building2, Clock, CalendarCheck, ArrowLeftRight, LogOut,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

// Las rutas del front replican las del backend Django desplegado
const navItems = [
  { to: '/',                   icon: LayoutDashboard, label: 'Dashboard'           },
  { to: '/salas',              icon: Building2,        label: 'Salas'               },
  { to: '/monitores',          icon: Monitor,          label: 'Monitores'           },
  { to: '/horarios',           icon: Clock,            label: 'Horarios'            },
  { to: '/asignaciones',       icon: CalendarCheck,    label: 'Asignaciones'        },
  { to: '/solicitudes-cambio', icon: ArrowLeftRight,   label: 'Solicitudes cambio'  },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const displayName = (user?.first_name && user?.last_name)
    ? `${user.first_name} ${user.last_name}`
    : user?.first_name || user?.email || 'Usuario'
  const initial = displayName.charAt(0).toUpperCase()

  return (
    <aside className="w-64 min-h-screen bg-sidebar flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-white/10">
        <p className="text-white font-bold text-lg leading-tight">SGMSC</p>
        <p className="text-white/50 text-xs mt-0.5">Gestión de Monitores</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
              ${isActive
                ? 'bg-primary text-white'
                : 'text-white/70 hover:bg-white/10 hover:text-white'}`
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="px-4 py-4 border-t border-white/10">
        {user && (
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold">
              {initial}
            </div>
            <div className="min-w-0">
              <p className="text-white text-xs font-medium truncate">{displayName}</p>
              <p className="text-white/50 text-xs capitalize">{user.rol || 'Sesión activa'}</p>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-white/70 hover:bg-white/10 hover:text-white text-sm transition-colors"
        >
          <LogOut className="w-4 h-4" /> Cerrar sesión
        </button>
      </div>
    </aside>
  )
}
