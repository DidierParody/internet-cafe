// Reglas de acceso de las rutas, como función pura para poder probarlas.

export type Access = 'public' | 'student' | 'admin'
export type Role = 'student' | 'admin' | null

export interface RouteAccess {
  access: Access
  /** Rutas como login o registro: quien ya inició sesión no debe verlas. */
  guestOnly?: boolean
}

export interface AuthState {
  authenticated: boolean
  role: Role
}

export type Redirect = { name: string; query?: Record<string, string> }

function homeFor(role: Role): Redirect {
  return role === 'admin' ? { name: 'admin-machines' } : { name: 'home' }
}

export function resolveAccess(
  meta: RouteAccess,
  fullPath: string,
  auth: AuthState,
): Redirect | null {
  if (meta.access === 'public') {
    return meta.guestOnly && auth.authenticated ? homeFor(auth.role) : null
  }
  if (!auth.authenticated) return { name: 'login', query: { next: fullPath } }
  if (meta.access === 'admin' && auth.role !== 'admin') return homeFor(auth.role)
  // La confirmación de acceso (/s) sirve a cualquier usuario autenticado.
  if (meta.access === 'student' && auth.role === 'admin' && fullPath !== '/s') {
    return homeFor(auth.role)
  }
  return null
}
