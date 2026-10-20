import { describe, expect, it } from 'vitest'

import { resolveAccess } from '@/router/guards'

const anon = { authenticated: false, role: null }
const student = { authenticated: true, role: 'student' as const }
const admin = { authenticated: true, role: 'admin' as const }

describe('resolveAccess', () => {
  it('manda al login a quien no ha iniciado sesión, recordando a dónde iba', () => {
    expect(resolveAccess({ access: 'student' }, '/historial', anon)).toEqual({
      name: 'login',
      query: { next: '/historial' },
    })
  })

  it('deja pasar las rutas públicas sin sesión', () => {
    expect(resolveAccess({ access: 'public' }, '/login', anon)).toBeNull()
  })

  it('saca del login a quien ya inició sesión según su rol', () => {
    expect(resolveAccess({ access: 'public', guestOnly: true }, '/login', student)).toEqual({
      name: 'home',
    })
    expect(resolveAccess({ access: 'public', guestOnly: true }, '/login', admin)).toEqual({
      name: 'admin-machines',
    })
  })

  it('protege el panel admin de los estudiantes', () => {
    expect(resolveAccess({ access: 'admin' }, '/admin/equipos', student)).toEqual({ name: 'home' })
    expect(resolveAccess({ access: 'admin' }, '/admin/equipos', admin)).toBeNull()
  })

  it('lleva al admin a su panel desde las pantallas de estudiante', () => {
    expect(resolveAccess({ access: 'student' }, '/', admin)).toEqual({ name: 'admin-machines' })
  })

  it('permite la confirmación de acceso a cualquier usuario autenticado', () => {
    expect(resolveAccess({ access: 'student' }, '/s', student)).toBeNull()
  })
})
