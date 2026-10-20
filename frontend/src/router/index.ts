import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import { resolveAccess, type RouteAccess } from './guards'
import { captureScanToken } from './scanCapture'

declare module 'vue-router' {
  interface RouteMeta extends Partial<RouteAccess> {
    title?: string
  }
}

export const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { access: 'public', guestOnly: true, title: 'Inicia sesión' },
    },
    {
      path: '/registro',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { access: 'public', guestOnly: true, title: 'Crea tu cuenta' },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { access: 'student', title: 'Inicio' },
    },
    {
      path: '/escanear',
      name: 'scan',
      component: () => import('@/views/ScanView.vue'),
      meta: { access: 'student', title: 'Escanear QR' },
    },
    {
      path: '/s',
      name: 'confirm',
      component: () => import('@/views/ConfirmView.vue'),
      meta: { access: 'student', title: 'Confirmar acceso' },
    },
    {
      path: '/historial',
      name: 'history',
      component: () => import('@/views/HistoryView.vue'),
      meta: { access: 'student', title: 'Historial' },
    },
    {
      path: '/perfil',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { access: 'student', title: 'Perfil' },
    },
    { path: '/admin', redirect: { name: 'admin-machines' } },
    {
      path: '/admin/equipos',
      name: 'admin-machines',
      component: () => import('@/views/admin/AdminMachinesView.vue'),
      meta: { access: 'admin', title: 'Salas y equipos' },
    },
    {
      path: '/admin/equipos/:id',
      name: 'admin-machine',
      component: () => import('@/views/admin/AdminMachineView.vue'),
      meta: { access: 'admin', title: 'Detalle de equipo' },
    },
    {
      path: '/admin/accesos',
      name: 'admin-sessions',
      component: () => import('@/views/admin/AdminSessionsView.vue'),
      meta: { access: 'admin', title: 'Accesos' },
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'home' } },
  ],
})

router.beforeEach(async (to) => {
  const strip = captureScanToken(to)
  if (strip) return strip
  const auth = useAuthStore()
  await auth.bootstrap()
  const redirect = resolveAccess(
    { access: to.meta.access ?? 'student', guestOnly: to.meta.guestOnly },
    to.name === 'confirm' ? '/s' : to.fullPath,
    { authenticated: auth.authenticated, role: auth.role },
  )
  return redirect ?? true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · AccesoLab` : 'AccesoLab'
})
