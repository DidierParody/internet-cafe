<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { adminApi, type AdminSessionOut, type MachineOut } from '@/api/endpoints'
import AdminShell from '@/components/AdminShell.vue'
import { messageFor } from '@/lib/errors'
import { endReasonLabel, formatDuration, secondsSince, shortDateTime } from '@/lib/format'

import { reasonChip } from './labels'

type Filter = 'todas' | 'activas' | 'cerradas'

const route = useRoute()
const machines = ref<MachineOut[]>([])
const items = ref<AdminSessionOut[]>([])
const cursor = ref<string | null>(null)
const filter = ref<Filter>('todas')
const machineId = ref(typeof route.query.equipo === 'string' ? route.query.equipo : '')
const loading = ref(false)
const error = ref<string | null>(null)

function activeParam(): boolean | null {
  return filter.value === 'activas' ? true : filter.value === 'cerradas' ? false : null
}

async function load(more = false): Promise<void> {
  error.value = null
  loading.value = true
  try {
    const page = await adminApi.sessions({
      active: activeParam(),
      machineId: machineId.value || null,
      limit: 50,
      cursor: more ? cursor.value : null,
    })
    items.value = more ? [...items.value, ...page.items] : page.items
    cursor.value = page.next_cursor ?? null
  } catch (e) {
    error.value = messageFor(e)
  } finally {
    loading.value = false
  }
}

async function forceEnd(id: string): Promise<void> {
  try {
    const updated = await adminApi.endSession(id)
    items.value = items.value.map((s) => (s.id === id ? updated : s))
  } catch (e) {
    error.value = messageFor(e)
  }
}

watch([filter, machineId], () => void load())

onMounted(async () => {
  await load()
  try {
    machines.value = await adminApi.machines()
  } catch (e) {
    error.value = messageFor(e)
  }
})
</script>

<template>
  <AdminShell>
    <div>
      <h1>Accesos</h1>
      <p class="muted lead">Quién usó cada equipo, cuándo empezó y cómo terminó la sesión.</p>
    </div>

    <div class="filters">
      <fieldset class="segment">
        <legend class="filter-label">Estado</legend>
        <div class="segmented">
          <label
            v-for="opt in [
              { v: 'todas', t: 'Todas' },
              { v: 'activas', t: 'Activas' },
              { v: 'cerradas', t: 'Cerradas' },
            ]"
            :key="opt.v"
            :for="`f-${opt.v}`"
            :class="{ on: filter === opt.v }"
          >
            <input :id="`f-${opt.v}`" v-model="filter" type="radio" :value="opt.v" />{{ opt.t }}
          </label>
        </div>
      </fieldset>
      <div class="field">
        <label for="f-equipo" class="filter-label">Equipo</label>
        <select id="f-equipo" v-model="machineId" class="input input-sm machine-select">
          <option value="">Todos los equipos</option>
          <option v-for="m in machines" :key="m.id" :value="m.id">{{ m.code }}</option>
        </select>
      </div>
    </div>

    <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>

    <section class="card" aria-label="Lista de accesos" :aria-busy="loading">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Estudiante</th>
              <th scope="col">Equipo</th>
              <th scope="col">Inicio</th>
              <th scope="col">Fin</th>
              <th scope="col">Duración</th>
              <th scope="col">Cierre</th>
              <th scope="col"><span class="sr-only">Acciones</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in items" :key="s.id">
              <td>
                <span class="cell-stack">
                  <span class="strong">{{ s.student_name }}</span>
                  <span class="mono sub">{{ s.student_code_masked }}</span>
                </span>
              </td>
              <td>
                <span class="cell-stack">
                  <span class="mono strong">{{ s.machine.code }}</span>
                  <span class="sub">{{ s.machine.lab ?? 'Sin sala' }}</span>
                </span>
              </td>
              <td>{{ shortDateTime(s.started_at) }}</td>
              <td>{{ s.ended_at ? shortDateTime(s.ended_at) : '—' }}</td>
              <td>
                {{
                  formatDuration(
                    s.status === 'active' ? secondsSince(s.started_at) : (s.duration_s ?? 0),
                  )
                }}
              </td>
              <td>
                <span v-if="s.status === 'active'" class="chip chip-success">
                  <span class="dot" />En curso
                </span>
                <span v-else class="chip" :class="reasonChip(s.end_reason)">
                  {{ endReasonLabel(s.end_reason) }}
                </span>
              </td>
              <td class="right">
                <button
                  v-if="s.status === 'active'"
                  type="button"
                  class="btn btn-danger small-btn"
                  @click="forceEnd(s.id)"
                >
                  Forzar cierre
                </button>
              </td>
            </tr>
            <tr v-if="!items.length && !loading">
              <td colspan="7" class="muted empty">No hay accesos con estos filtros.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="foot">
        <span class="muted small">
          Mostrando {{ items.length }} accesos, del más reciente al más antiguo
        </span>
        <button
          v-if="cursor"
          type="button"
          class="btn btn-outline"
          :disabled="loading"
          @click="load(true)"
        >
          Cargar más
        </button>
      </div>
    </section>
  </AdminShell>
</template>

<style scoped src="./admin.css"></style>
<style scoped>
.lead {
  margin-top: 4px;
  font-size: 15px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 16px;
}
.segment {
  margin: 0;
  padding: 0;
  border: 0;
}
.filter-label {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}
.segmented {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 12px;
  background: #e9edf4;
}
.segmented label {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 9px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-2);
  cursor: pointer;
}
.segmented label.on {
  background: var(--surface);
  color: var(--ink);
  font-weight: 600;
}
.segmented input {
  margin: 0;
  accent-color: var(--primary);
}
.machine-select {
  min-width: 200px;
}
table {
  min-width: 860px;
}
.small-btn {
  min-height: 36px;
  padding: 0 12px;
  font-size: 13px;
  border-radius: 9px;
}
.foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 20px;
  border-top: 1px solid var(--divider);
}
.small {
  font-size: 14px;
}
</style>
