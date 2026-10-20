// Formatos de fechas, duraciones y motivos de cierre en español.

const END_REASONS: Record<string, string> = {
  user_logout_pc: 'Cerrada en el equipo',
  user_logout_web: 'Cerrada desde el celular',
  superseded: 'Cambio de equipo',
  heartbeat_timeout: 'Cerrada por inactividad',
  admin_forced: 'Forzada por admin',
  machine_shutdown: 'Equipo apagado',
}

export function endReasonLabel(reason: string | null | undefined): string {
  return reason ? (END_REASONS[reason] ?? reason) : ''
}

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.floor(seconds / 60)
  if (totalMinutes < 1) return 'menos de 1 min'
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours === 0) return `${minutes} min`
  if (minutes === 0) return `${hours} h`
  return `${hours} h ${String(minutes).padStart(2, '0')} min`
}

export function secondsSince(iso: string, now: Date = new Date()): number {
  return Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 1000))
}

const timeFormat = new Intl.DateTimeFormat('es', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})
const dayFormat = new Intl.DateTimeFormat('es', { day: 'numeric', month: 'long' })
const shortDayFormat = new Intl.DateTimeFormat('es', { day: 'numeric', month: 'short' })

export function timeHM(iso: string): string {
  return timeFormat.format(new Date(iso))
}

function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
}

export function dayLabel(date: Date, now: Date = new Date()): string {
  const diffDays = Math.round((startOfDay(now) - startOfDay(date)) / 86_400_000)
  if (diffDays === 0) return 'Hoy'
  if (diffDays === 1) return 'Ayer'
  return dayFormat.format(date)
}

/** "Hoy, 10:24" · "Ayer, 16:40" · "16 oct, 11:20" */
export function shortDateTime(iso: string, now: Date = new Date()): string {
  const date = new Date(iso)
  const label = dayLabel(date, now)
  const day = label === 'Hoy' || label === 'Ayer' ? label : shortDayFormat.format(date)
  return `${day}, ${timeHM(iso)}`
}

export interface DayGroup<T> {
  label: string
  items: T[]
}

export function groupByDay<T extends { started_at: string }>(
  items: T[],
  now: Date = new Date(),
): DayGroup<T>[] {
  const groups: DayGroup<T>[] = []
  for (const item of items) {
    const label = dayLabel(new Date(item.started_at), now)
    const last = groups[groups.length - 1]
    if (last && last.label === label) last.items.push(item)
    else groups.push({ label, items: [item] })
  }
  return groups
}

export function initials(fullName: string): string {
  return fullName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}
