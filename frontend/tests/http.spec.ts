import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, ApiError, onSessionExpired, setAccessToken } from '@/api/http'

function json(status: number, body: unknown, type = 'application/json'): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { 'content-type': type },
  })
}

const tokenOut = (token: string) => ({
  access_token: token,
  token_type: 'Bearer',
  expires_in: 600,
  user: { id: 'u1', full_name: 'Ana Pérez', role: 'student' },
})

describe('api()', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
    setAccessToken(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('envía el token de acceso y devuelve el JSON', async () => {
    setAccessToken('tok-1')
    fetchMock.mockResolvedValueOnce(json(200, { ok: true }))
    await expect(api('/me')).resolves.toEqual({ ok: true })
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/v1/me')
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer tok-1')
    expect(init?.credentials).toBe('same-origin')
  })

  it('renueva el token una vez ante AUTH_TOKEN_EXPIRED y reintenta', async () => {
    setAccessToken('viejo')
    fetchMock
      .mockResolvedValueOnce(
        json(
          401,
          { code: 'AUTH_TOKEN_EXPIRED', title: 'x', status: 401 },
          'application/problem+json',
        ),
      )
      .mockResolvedValueOnce(json(200, tokenOut('nuevo')))
      .mockResolvedValueOnce(json(200, { ok: true }))
    await expect(api('/me')).resolves.toEqual({ ok: true })
    expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/v1/auth/refresh')
    const retry = fetchMock.mock.calls[2]?.[1]
    expect(new Headers(retry?.headers).get('Authorization')).toBe('Bearer nuevo')
  })

  it('avisa que la sesión expiró si la renovación falla', async () => {
    const expired = vi.fn()
    onSessionExpired(expired)
    setAccessToken('viejo')
    fetchMock
      .mockResolvedValueOnce(json(401, { code: 'AUTH_TOKEN_EXPIRED', title: 'x', status: 401 }))
      .mockResolvedValueOnce(json(401, { code: 'AUTH_REFRESH_INVALID', title: 'x', status: 401 }))
    await expect(api('/me')).rejects.toMatchObject({ status: 401 })
    expect(expired).toHaveBeenCalledOnce()
  })

  it('convierte un Problem Details en ApiError con su code', async () => {
    fetchMock.mockResolvedValueOnce(
      json(
        410,
        { code: 'CHALLENGE_EXPIRED', title: 'El código QR expiró', status: 410 },
        'application/problem+json',
      ),
    )
    const error = (await api('/scan/preview', { method: 'POST', body: {} }).catch(
      (e: unknown) => e,
    )) as ApiError
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 410, code: 'CHALLENGE_EXPIRED' })
    expect(error.message).toBe('El código QR expiró')
  })

  it('envía el cuerpo como JSON y acepta 204 sin contenido', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    await expect(api('/auth/logout', { method: 'POST', auth: false })).resolves.toBeUndefined()
    fetchMock.mockResolvedValueOnce(json(202, { status: 'accepted' }))
    await api('/auth/register', { method: 'POST', body: { a: 1 }, auth: false })
    const init = fetchMock.mock.calls[1]?.[1]
    expect(init?.body).toBe('{"a":1}')
    expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
  })
})
