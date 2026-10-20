// El QR del equipo codifica `https://<front>/s#<token>`. El token va en el fragmento para
// que nunca llegue a los logs de Vercel ni de la API (sección 12.5 del SRS).

const TOKEN_RE = /^[A-Za-z0-9_-]{20,100}$/

export function tokenFromHash(hash: string): string | null {
  const value = hash.startsWith('#') ? hash.slice(1) : hash
  return TOKEN_RE.test(value) ? value : null
}

/** Solo acepta QR del propio dominio con la ruta /s (RN-11). */
export function tokenFromQrText(text: string, origin: string): string | null {
  let url: URL
  try {
    url = new URL(text.trim())
  } catch {
    return null
  }
  if (url.origin !== origin || url.pathname !== '/s') return null
  return tokenFromHash(url.hash)
}
