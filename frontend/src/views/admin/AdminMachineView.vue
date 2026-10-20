<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import {
  adminApi,
  type AdminSessionOut,
  type EnrollmentCodeOut,
  type LabOut,
  type MachineOut,
} from '@/api/endpoints'
import AdminShell from '@/components/AdminShell.vue'
import AppIcon from '@/components/AppIcon.vue'
import { messageFor } from '@/lib/errors'
import { endReasonLabel, formatDuration, secondsSince, shortDateTime, timeHM } from '@/lib/format'

import { reasonChip, STATUS_CHIP, STATUS_LABEL } from './labels'

const route = useRoute()
const id = computed(() => String(route.params.id))

const machine = ref<MachineOut | null>(null)
const labs = ref<LabOut[]>([])
const sessions = ref<AdminSessionOut[]>([])
const notFound = ref(false)
const error = ref<string | null>(null)

const code = ref<EnrollmentCodeOut | null>(null)
const codeError = ref<string | null>(null)
const copied = ref(false)

const config = reactive({ labId: '', mode: 'passive' as 'passive' | 'kiosk', enabled: true })
const saving = ref(false)
const configMessage = ref<{ ok: boolean; text: string } | null>(null)

const current = computed(() => sessions.value.find((s) => s.status === 'active') ?? null)
const recent = computed(() => sessions.value.filter((s) => s.status === 'ended'))

function syncConfig(m: MachineOut): void {
  config.labId = m.lab_id ?? ''
  config.mode = m.mode === 'kiosk' ? 'kiosk' : 'passive'
  config.enabled = m.status !== 'disabled'
}

async function loadSessions(): Promise<void> {
  sessions.value = (await adminApi.sessions({ machineId: id.value, limit: 6 })).items
}

async function load(): Promise<void> {
  error.value = null
  try {
    const [all, l] = await Promise.all([adminApi.machines(), adminApi.labs()])
    labs.value = l
    machine.value = all.find((m) => m.id === id.value) ?? null
    notFound.value = machine.value === null
    if (machine.value) {
      syncConfig(machine.value)
      await loadSessions()
    }
  } catch (e) {
    error.value = messageFor(e)
  }
}

async function generateCode(): Promise<void> {
  codeError.value = null
  copied.value = false
  try {
    code.value = await adminApi.enrollmentCode(id.value)
  } catch (e) {
    codeError.value = messageFor(e)
  }
}

async function copyCode(): Promise<void> {
  if (!code.value) return
  await navigator.clipboard.writeText(code.value.code)
  copied.value = true
}

async function save(): Promise<void> {
  if (!machine.value) return
  configMessage.value = null
  saving.value = true
  try {
    const enrolled = machine.value.status !== 'pending_enrollment'
    machine.value = await adminApi.updateMachine(id.value, {
      lab_id: config.labId || null,
      mode: config.mode,
      ...(enrolled ? { status: config.enabled ? 'active' : 'disabled' } : {}),
    })
    syncConfig(machine.value)
    configMessage.value = { ok: true, text: 'Cambios guardados.' }
  } catch (e) {
    configMessage.value = { ok: false, text: messageFor(e) }
  } finally {
    saving.value = false
  }
}

async function forceEnd(sessionId: string): Promise<void> {
  try {
    await adminApi.endSession(sessionId)
    await loadSessions()
  } catch (e) {
    error.value = messageFor(e)
  }
}

onMounted(() => void load())
</script>

<template>
  <AdminShell>
    <nav aria-label="Ruta" class="crumbs">
      <RouterLink :to="{ name: 'admin-machines' }" class="strong">Salas y equipos</RouterLink>
      <span aria-hidden="true"> › </span>{{ machine?.code ?? '…' }}
    </nav>

    <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>
    <p v-if="notFound" class="card notice">Este equipo no existe o fue eliminado.</p>

    <template v-if="machine">
      <div class="title-row">
        <h1 class="mono code">{{ machine.code }}</h1>
        <span class="chip big" :class="STATUS_CHIP[machine.status]">
          {{ STATUS_LABEL[machine.status] }}
        </span>
        <span class="chip big outline">
          <span class="dot" :class="{ 'dot-off': !machine.online }" />
          {{ machine.online ? 'En línea' : 'Desconectado' }}
        </span>
      </div>
      <p class="muted meta">
        {{ machine.lab ?? 'Sin sala' }}
        <template v-if="machine.app_version"> · versión {{ machine.app_version }}</template>
      </p>

      <div class="columns">
        <div class="main-col">
          <section class="card current" aria-labelledby="actual-titulo">
            <div class="current-text">
              <h2 id="actual-titulo" class="eyebrow">Sesión actual</h2>
              <template v-if="current">
                <span class="who">
                  {{ current.student_name }}
                  <span class="mono sub">{{ current.student_code_masked }}</span>
                </span>
                <span class="muted small">
                  Desde las {{ timeHM(current.started_at) }} ·
                  {{ formatDuration(secondsSince(current.started_at)) }}
                </span>
              </template>
              <span v-else class="muted small">Nadie está usando este equipo ahora.</span>
            </div>
            <button
              v-if="current"
              type="button"
              class="btn btn-danger"
              @click="forceEnd(current.id)"
            >
              Forzar cierre
            </button>
          </section>

          <section class="card" aria-labelledby="hist-titulo">
            <h2 id="hist-titulo" class="card-title">Últimos accesos del equipo</h2>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Estudiante</th>
                    <th scope="col">Inicio</th>
                    <th scope="col">Duración</th>
                    <th scope="col">Cierre</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in recent" :key="s.id">
                    <td>
                      {{ s.student_name }}
                      <span class="mono sub">{{ s.student_code_masked }}</span>
                    </td>
                    <td>{{ shortDateTime(s.started_at) }}</td>
                    <td>{{ formatDuration(s.duration_s ?? 0) }}</td>
                    <td>
                      <span class="chip" :class="reasonChip(s.end_reason)">
                        {{ endReasonLabel(s.end_reason) }}
                      </span>
                    </td>
                  </tr>
                  <tr v-if="!recent.length">
                    <td colspan="4" class="muted empty">Todavía no hay accesos cerrados.</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="card-foot">
              <RouterLink
                :to="{ name: 'admin-sessions', query: { equipo: machine.id } }"
                class="strong"
              >
                Ver todos los accesos de este equipo
              </RouterLink>
            </div>
          </section>
        </div>

        <div class="side-col">
          <section class="card side" aria-labelledby="enrol-titulo">
            <h2 id="enrol-titulo">Enrolamiento</h2>
            <template v-if="code">
              <div class="code-box">
                <span class="mono enroll-code">{{ code.code }}</span>
                <button
                  type="button"
                  class="btn btn-outline icon-only"
                  aria-label="Copiar código"
                  @click="copyCode"
                >
                  <AppIcon :name="copied ? 'check' : 'copy'" :size="20" />
                </button>
              </div>
              <p class="alert alert-warn small" role="status">
                {{ copied ? 'Código copiado. ' : '' }}Se muestra una sola vez y vence en 24 h.
                Ingrésalo en la aplicación del equipo.
              </p>
            </template>
            <p v-else class="muted small">
              Genera un código de un solo uso para enrolar o reenrolar este equipo.
            </p>
            <p v-if="codeError" class="alert alert-error" role="alert">{{ codeError }}</p>
            <button type="button" class="btn btn-outline-primary" @click="generateCode">
              {{ code ? 'Generar otro código' : 'Generar código' }}
            </button>
          </section>

          <section class="card side" aria-labelledby="config-titulo">
            <h2 id="config-titulo">Configuración</h2>
            <form class="form" novalidate @submit.prevent="save">
              <div class="field">
                <label for="c-sala">Sala</label>
                <select id="c-sala" v-model="config.labId" class="input input-sm">
                  <option value="">Sin sala</option>
                  <option v-for="lab in labs" :key="lab.id" :value="lab.id">{{ lab.name }}</option>
                </select>
              </div>
              <fieldset class="modes">
                <legend class="field-label">Modo</legend>
                <div class="segmented">
                  <label for="m-pasivo" :class="{ on: config.mode === 'passive' }">
                    <input id="m-pasivo" v-model="config.mode" type="radio" value="passive" />Pasivo
                  </label>
                  <label for="m-kiosco" :class="{ on: config.mode === 'kiosk' }">
                    <input id="m-kiosco" v-model="config.mode" type="radio" value="kiosk" />Kiosco
                  </label>
                </div>
                <p class="hint">El equipo aplica el cambio en su próximo latido (máximo 60 s).</p>
              </fieldset>
              <label for="c-habilitado" class="toggle">
                <span class="toggle-text">
                  <strong>Equipo habilitado</strong>
                  <span class="hint">
                    {{
                      machine.status === 'pending_enrollment'
                        ? 'Se habilita al enrolarse.'
                        : 'Si lo deshabilitas, deja de mostrar QR.'
                    }}
                  </span>
                </span>
                <input
                  id="c-habilitado"
                  v-model="config.enabled"
                  type="checkbox"
                  :disabled="machine.status === 'pending_enrollment'"
                />
              </label>
              <p
                v-if="configMessage"
                class="alert"
                :class="configMessage.ok ? 'alert-success' : 'alert-error'"
                role="status"
              >
                {{ configMessage.text }}
              </p>
              <button type="submit" class="btn btn-primary" :disabled="saving">
                {{ saving ? 'Guardando…' : 'Guardar cambios' }}
              </button>
            </form>
          </section>
        </div>
      </div>
    </template>
  </AdminShell>
</template>

<style scoped src="./admin.css"></style>
<style scoped>
.crumbs {
  font-size: 14px;
  color: var(--muted);
}
.notice {
  padding: 18px 20px;
}
.title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.code {
  font-size: 30px;
  font-weight: 600;
}
.big {
  font-size: 13px;
  padding: 4px 10px;
}
.outline {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--ink);
}
.meta {
  margin-top: -10px;
  font-size: 15px;
}
.main-col {
  flex: 999 1 520px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.side-col {
  flex: 1 1 320px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.current {
  padding: 18px 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
}
.current-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-right: auto;
}
.eyebrow {
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.who {
  font-size: 18px;
  font-weight: 700;
}
.small {
  font-size: 14px;
}
.card-title {
  padding: 16px 20px;
  border-bottom: 1px solid var(--divider);
}
table {
  min-width: 560px;
}
.card-foot {
  padding: 12px 20px;
  border-top: 1px solid var(--divider);
  font-size: 14px;
}
.code-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px dashed #9db3ee;
  background: #f5f8ff;
}
.enroll-code {
  font-size: 26px;
  font-weight: 600;
  letter-spacing: 0.06em;
}
.icon-only {
  width: 44px;
  padding: 0;
  border-radius: 10px;
}
.segmented {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  padding: 4px;
  border-radius: 12px;
  background: var(--bg);
}
.segmented label {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  border-radius: 9px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-2);
  cursor: pointer;
}
.segmented label.on {
  background: var(--surface);
  border: 1px solid var(--input-border);
  color: var(--ink);
  font-weight: 600;
}
.segmented input {
  margin: 0;
  accent-color: var(--primary);
}
.modes .hint {
  margin-top: 8px;
}
.toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
}
.toggle-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 14px;
}
.toggle input {
  width: 22px;
  height: 22px;
  margin: 0;
  accent-color: var(--primary);
}
</style>
