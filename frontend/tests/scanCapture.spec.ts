import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { captureScanToken } from '@/router/scanCapture'
import { useScanStore } from '@/stores/scan'

const TOKEN = 'Sc2idKx2ECjLjoz_H-cceVu3y07n1cG6zl206IASeqo'

describe('captureScanToken', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('guarda el token en memoria y redirige a /s sin fragmento', () => {
    expect(captureScanToken({ name: 'confirm', hash: `#${TOKEN}` })).toEqual({
      name: 'confirm',
      replace: true,
    })
    expect(useScanStore().token).toBe(TOKEN)
  })

  it('también quita de la URL un fragmento que no es un token válido', () => {
    expect(captureScanToken({ name: 'confirm', hash: '#basura' })).toEqual({
      name: 'confirm',
      replace: true,
    })
    expect(useScanStore().token).toBeNull()
  })

  it('no toca otras rutas ni /s sin fragmento', () => {
    expect(captureScanToken({ name: 'home', hash: `#${TOKEN}` })).toBeNull()
    expect(captureScanToken({ name: 'confirm', hash: '' })).toBeNull()
  })
})
