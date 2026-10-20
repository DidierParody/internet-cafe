// Funciones tipadas por endpoint. Los tipos vienen del contrato OpenAPI (npm run gen:api).

import { api } from './http'
import type { components } from './schema'

type S = components['schemas']

export type TokenOut = S['TokenOut']
export type UserSummary = S['UserSummary']
export type MeOut = S['MeOut']
export type SessionOut = S['SessionOut']
export type SessionPage = S['SessionPage']
export type PreviewOut = S['PreviewOut']
export type ClaimOut = S['ClaimOut']
export type LabOut = S['LabOut']
export type MachineOut = S['MachineOut']
export type EnrollmentCodeOut = S['EnrollmentCodeOut']
export type AdminSessionOut = S['AdminSessionOut']
export type AdminSessionPage = S['AdminSessionPage']

export const authApi = {
  register: (body: S['RegisterIn']) =>
    api<S['Accepted']>('/auth/register', { method: 'POST', body, auth: false }),
  login: (body: S['LoginIn']) =>
    api<TokenOut>('/auth/login', { method: 'POST', body, auth: false }),
  logout: () => api<void>('/auth/logout', { method: 'POST', auth: false }),
}

export const meApi = {
  get: () => api<MeOut>('/me'),
  changePassword: (body: S['ChangePasswordIn']) =>
    api<void>('/me/password', { method: 'PATCH', body }),
  sessions: (limit = 20, cursor?: string | null) =>
    api<SessionPage>('/me/sessions', { query: { limit, cursor } }),
  activeSession: () => api<S['ActiveSessionOut']>('/me/sessions/active'),
  endSession: (id: string) => api<SessionOut>(`/me/sessions/${id}/end`, { method: 'POST' }),
}

export const scanApi = {
  preview: (token: string) => api<PreviewOut>('/scan/preview', { method: 'POST', body: { token } }),
  claim: (token: string) => api<ClaimOut>('/scan/claim', { method: 'POST', body: { token } }),
}

export const adminApi = {
  labs: () => api<LabOut[]>('/admin/labs'),
  createLab: (body: S['LabIn']) => api<LabOut>('/admin/labs', { method: 'POST', body }),
  machines: () => api<MachineOut[]>('/admin/machines'),
  createMachine: (body: S['MachineIn']) =>
    api<MachineOut>('/admin/machines', { method: 'POST', body }),
  updateMachine: (id: string, body: S['MachinePatch']) =>
    api<MachineOut>(`/admin/machines/${id}`, { method: 'PATCH', body }),
  enrollmentCode: (id: string) =>
    api<EnrollmentCodeOut>(`/admin/machines/${id}/enrollment-codes`, { method: 'POST' }),
  sessions: (params: {
    active?: boolean | null
    machineId?: string | null
    limit?: number
    cursor?: string | null
  }) =>
    api<AdminSessionPage>('/admin/sessions', {
      query: {
        active: params.active,
        machine_id: params.machineId,
        limit: params.limit ?? 50,
        cursor: params.cursor,
      },
    }),
  endSession: (id: string) => api<AdminSessionOut>(`/admin/sessions/${id}/end`, { method: 'POST' }),
}
