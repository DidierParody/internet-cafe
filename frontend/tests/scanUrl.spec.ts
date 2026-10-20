import { describe, expect, it } from 'vitest'

import { tokenFromHash, tokenFromQrText } from '@/lib/scanUrl'

const TOKEN = 'Sc2idKx2ECjLjoz_H-cceVu3y07n1cG6zl206IASeqo'
const ORIGIN = 'https://acceso.example'

describe('tokenFromHash', () => {
  it('lee el token del fragmento', () => {
    expect(tokenFromHash(`#${TOKEN}`)).toBe(TOKEN)
  })

  it('devuelve null si no hay fragmento o no parece un token', () => {
    expect(tokenFromHash('')).toBeNull()
    expect(tokenFromHash('#corto')).toBeNull()
    expect(tokenFromHash('#<script>alert(1)</script>xxxxxxxxxxxxx')).toBeNull()
  })
})

describe('tokenFromQrText', () => {
  it('acepta la URL del propio dominio con la ruta /s', () => {
    expect(tokenFromQrText(`${ORIGIN}/s#${TOKEN}`, ORIGIN)).toBe(TOKEN)
  })

  it('rechaza un QR de otro dominio', () => {
    expect(tokenFromQrText(`https://otro.example/s#${TOKEN}`, ORIGIN)).toBeNull()
  })

  it('rechaza otra ruta del mismo dominio', () => {
    expect(tokenFromQrText(`${ORIGIN}/login#${TOKEN}`, ORIGIN)).toBeNull()
  })

  it('rechaza texto que no es una URL', () => {
    expect(tokenFromQrText('hola mundo', ORIGIN)).toBeNull()
  })
})
