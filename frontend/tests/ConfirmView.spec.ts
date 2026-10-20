import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { ApiError } from '@/api/http'
import { useScanStore } from '@/stores/scan'
import ConfirmView from '@/views/ConfirmView.vue'

const { preview, claim } = vi.hoisted(() => ({ preview: vi.fn(), claim: vi.fn() }))
vi.mock('@/api/endpoints', () => ({ scanApi: { preview, claim } }))

const TOKEN = 'Sc2idKx2ECjLjoz_H-cceVu3y07n1cG6zl206IASeqo'
const machine = { id: 'm1', code: 'LAB3-PC12', lab: 'Sala 3 · Bloque B' }

function inSeconds(seconds: number): string {
  return new Date(Date.now() + seconds * 1000).toISOString()
}

async function render(token: string | null = TOKEN) {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (token) useScanStore().set(token)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/s', name: 'confirm', component: ConfirmView },
      { path: '/escanear', name: 'scan', component: { template: '<div />' } },
    ],
  })
  await router.push('/s')
  const wrapper = mount(ConfirmView, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return wrapper
}

describe('ConfirmView', () => {
  beforeEach(() => {
    preview.mockReset()
    claim.mockReset()
  })

  it('muestra el equipo y la sala antes de confirmar, sin consumir el QR', async () => {
    preview.mockResolvedValue({ machine, expires_at: inSeconds(42), active_session: null })
    const wrapper = await render()
    expect(preview).toHaveBeenCalledWith(TOKEN)
    expect(wrapper.text()).toContain('LAB3-PC12')
    expect(wrapper.text()).toContain('Sala 3 · Bloque B')
    expect(wrapper.text()).toMatch(/vence en 0:4\d/)
    expect(claim).not.toHaveBeenCalled()
  })

  it('advierte cuando el estudiante tiene una sesión abierta en otro equipo', async () => {
    preview.mockResolvedValue({
      machine,
      expires_at: inSeconds(42),
      active_session: { machine_code: 'LAB1-PC03' },
    })
    const wrapper = await render()
    expect(wrapper.text()).toContain('Tienes una sesión abierta en LAB1-PC03')
  })

  it('confirma el acceso y muestra el éxito', async () => {
    preview.mockResolvedValue({ machine, expires_at: inSeconds(42), active_session: null })
    claim.mockResolvedValue({
      session: { id: 's1', status: 'active', started_at: new Date().toISOString(), machine },
    })
    const wrapper = await render()
    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()
    expect(claim).toHaveBeenCalledWith(TOKEN)
    expect(wrapper.text()).toContain('¡Listo! Ya puedes usar el equipo')
    expect(useScanStore().token).toBeNull()
  })

  it('muestra el estado de QR vencido', async () => {
    preview.mockRejectedValue(new ApiError(410, 'CHALLENGE_EXPIRED', 'El código QR expiró'))
    const wrapper = await render()
    expect(wrapper.text()).toContain('El código QR expiró')
    expect(wrapper.find('a[href="/escanear"]').exists()).toBe(true)
  })

  it('muestra el estado de QR ya usado al confirmar', async () => {
    preview.mockResolvedValue({ machine, expires_at: inSeconds(42), active_session: null })
    claim.mockRejectedValue(new ApiError(409, 'CHALLENGE_ALREADY_USED', 'Ya se usó'))
    const wrapper = await render()
    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Este código ya se usó')
  })

  it('recarga la vista previa si llega un QR nuevo estando ya en /s', async () => {
    preview.mockRejectedValueOnce(new ApiError(410, 'CHALLENGE_EXPIRED', 'El código QR expiró'))
    const wrapper = await render()
    expect(wrapper.text()).toContain('El código QR expiró')
    preview.mockResolvedValueOnce({ machine, expires_at: inSeconds(50), active_session: null })
    useScanStore().set('OtroTokenNuevo_0123456789abcdefghijklmnopq')
    await flushPromises()
    expect(preview).toHaveBeenLastCalledWith('OtroTokenNuevo_0123456789abcdefghijklmnopq')
    expect(wrapper.text()).toContain('Vas a iniciar sesión en')
  })

  it('pide escanear si no hay un QR en memoria', async () => {
    const wrapper = await render(null)
    expect(preview).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('No encontramos el código del equipo')
  })
})
