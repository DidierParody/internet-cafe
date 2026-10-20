import { describe, expect, it } from 'vitest'

import { dayLabel, endReasonLabel, formatDuration, groupByDay, timeHM } from '@/lib/format'

describe('formatDuration', () => {
  it.each([
    [4320, '1 h 12 min'],
    [7500, '2 h 05 min'],
    [3600, '1 h'],
    [2880, '48 min'],
    [30, 'menos de 1 min'],
  ])('%i s → %s', (seconds, expected) => {
    expect(formatDuration(seconds)).toBe(expected)
  })
})

describe('endReasonLabel', () => {
  it('traduce los motivos de cierre', () => {
    expect(endReasonLabel('user_logout_pc')).toBe('Cerrada en el equipo')
    expect(endReasonLabel('user_logout_web')).toBe('Cerrada desde el celular')
    expect(endReasonLabel('superseded')).toBe('Cambio de equipo')
    expect(endReasonLabel('heartbeat_timeout')).toBe('Cerrada por inactividad')
    expect(endReasonLabel('admin_forced')).toBe('Forzada por admin')
    expect(endReasonLabel('machine_shutdown')).toBe('Equipo apagado')
    expect(endReasonLabel(null)).toBe('')
  })
})

describe('fechas', () => {
  const now = new Date(2026, 9, 20, 12, 0) // 20 de octubre de 2026, hora local

  it('etiqueta el día relativo', () => {
    expect(dayLabel(new Date(2026, 9, 20, 8, 0), now)).toBe('Hoy')
    expect(dayLabel(new Date(2026, 9, 19, 23, 0), now)).toBe('Ayer')
    expect(dayLabel(new Date(2026, 9, 16, 9, 0), now)).toBe('16 de octubre')
  })

  it('formatea la hora en 24 h', () => {
    expect(timeHM(new Date(2026, 9, 20, 9, 5).toISOString())).toBe('09:05')
  })

  it('agrupa por día conservando el orden', () => {
    const groups = groupByDay(
      [
        { id: 'a', started_at: new Date(2026, 9, 20, 10).toISOString() },
        { id: 'b', started_at: new Date(2026, 9, 19, 16).toISOString() },
        { id: 'c', started_at: new Date(2026, 9, 19, 9).toISOString() },
      ],
      now,
    )
    expect(groups.map((g) => g.label)).toEqual(['Hoy', 'Ayer'])
    expect(groups[1]?.items.map((i) => i.id)).toEqual(['b', 'c'])
  })
})
