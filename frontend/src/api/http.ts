// Cliente HTTP de la API (mismo origen: /api/v1, reenviado por Vercel o por el proxy de Vite).
//
// El access token vive SOLO en esta variable del módulo, en la memoria de la pestaña
// (nunca en localStorage ni en Pinia). El refresh token es una cookie HttpOnly que el
// navegador envía sola a /api/v1/auth.

import type { components } from './schema'

export const API_BASE = '/api/v1'

type TokenOut = components['schemas']['TokenOut']

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly detail: string | undefined

  constructor(status: number, code: string, title: string, detail?: string) {
    super(title)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detail = detail
  }
}

let accessToken: string | null = null
let expiredListener: (() => void) | null = null
let refreshInFlight: Promise<TokenOut | null> | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function hasAccessToken(): boolean {
  return accessToken !== null
}

export function onSessionExpired(listener: () => void): void {
  expiredListener = listener
}

async function toError(response: Response): Promise<ApiError> {
  let body: { code?: string; title?: string; detail?: string } = {}
  try {
    body = (await response.json()) as typeof body
  } catch {
    // Respuesta sin cuerpo JSON (p. ej. un 502 del proxy).
  }
  return new ApiError(
    response.status,
    body.code ?? `HTTP_${response.status}`,
    body.title ?? 'No se pudo completar la solicitud',
    body.detail,
  )
}

async function doRefresh(): Promise<TokenOut | null> {
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    credentials: 'same-origin',
  })
  if (!response.ok) {
    accessToken = null
    return null
  }
  const body = (await response.json()) as TokenOut
  accessToken = body.access_token
  return body
}

/**
 * Renueva el access token con la cookie de refresh. Las llamadas simultáneas de la
 * pestaña comparten una sola petición y las pestañas se coordinan con la Web Locks API,
 * para que dos pestañas no roten el mismo refresh token a la vez.
 */
export function refreshAccessToken(): Promise<TokenOut | null> {
  if (!refreshInFlight) {
    const locks = typeof navigator !== 'undefined' ? navigator.locks : undefined
    const run = locks ? locks.request('acceso-lab-refresh', doRefresh) : doRefresh()
    refreshInFlight = Promise.resolve(run).finally(() => {
      refreshInFlight = null
    })
  }
  return refreshInFlight
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  auth?: boolean
  query?: Record<string, string | number | boolean | null | undefined>
}

function buildUrl(path: string, query: RequestOptions['query']): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== null && value !== undefined && value !== '') params.set(key, String(value))
  }
  const qs = params.toString()
  return `${API_BASE}${path}${qs ? `?${qs}` : ''}`
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  const headers = new Headers()
  if (options.auth !== false && accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  let body: string | undefined
  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(options.body)
  }
  return fetch(buildUrl(path, options.query), {
    method: options.method ?? 'GET',
    headers,
    body,
    credentials: 'same-origin',
  })
}

export async function api<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await send(path, options)
  if (response.status === 401 && options.auth !== false) {
    const refreshed = await refreshAccessToken()
    if (!refreshed) {
      expiredListener?.()
      throw await toError(response)
    }
    response = await send(path, options)
  }
  if (!response.ok) throw await toError(response)
  if (response.status === 204) return undefined as T
  const text = await response.text()
  return (text ? JSON.parse(text) : undefined) as T
}
