import { tokenFromHash } from '@/lib/scanUrl'
import { useScanStore } from '@/stores/scan'

/**
 * El QR abre `/s#<token>`. El token se guarda en memoria y la navegación se redirige a
 * `/s` sin fragmento, para que no quede en la barra de direcciones ni en el historial.
 */
export function captureScanToken(to: {
  name?: unknown
  hash: string
}): { name: 'confirm'; replace: true } | null {
  if (to.name !== 'confirm' || !to.hash) return null
  const token = tokenFromHash(to.hash)
  if (token) useScanStore().set(token)
  return { name: 'confirm', replace: true }
}
