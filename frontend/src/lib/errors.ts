import { ApiError } from '@/api/http'

const MESSAGES: Record<string, string> = {
  AUTH_INVALID_CREDENTIALS: 'Correo o contraseña incorrectos.',
  AUTH_ACCOUNT_LOCKED: 'Demasiados intentos fallidos. Tu cuenta quedó bloqueada 15 minutos.',
  AUTH_EMAIL_NOT_VERIFIED: 'Debes verificar tu correo antes de iniciar sesión.',
  RATE_LIMITED: 'Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.',
  FORBIDDEN: 'No tienes permisos para hacer esto.',
  CONFLICT: 'Ya existe un registro con ese nombre o código.',
}

/** Mensaje accionable para mostrar al usuario a partir de un error de la API. */
export function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'VALIDATION_ERROR') {
      return error.message === 'Datos inválidos'
        ? 'Revisa los datos del formulario.'
        : error.message
    }
    return MESSAGES[error.code] ?? error.detail ?? error.message
  }
  return 'No pudimos conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.'
}

export function errorCode(error: unknown): string | null {
  return error instanceof ApiError ? error.code : null
}
