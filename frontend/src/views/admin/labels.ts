export const STATUS_LABEL: Record<string, string> = {
  active: 'Activo',
  pending_enrollment: 'Pendiente de enrolar',
  disabled: 'Deshabilitado',
}

export const STATUS_CHIP: Record<string, string> = {
  active: 'chip-success',
  pending_enrollment: 'chip-info',
  disabled: 'chip-neutral',
}

export const MODE_LABEL: Record<string, string> = {
  passive: 'Pasivo',
  kiosk: 'Kiosco',
}

export function reasonChip(reason: string | null | undefined): string {
  if (reason === 'heartbeat_timeout') return 'chip-warn'
  if (reason === 'admin_forced') return 'chip-danger'
  return 'chip-neutral'
}
