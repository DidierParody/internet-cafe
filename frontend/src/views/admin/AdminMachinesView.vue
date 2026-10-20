<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { adminApi, type LabOut, type MachineOut } from '@/api/endpoints'
import AdminShell from '@/components/AdminShell.vue'
import { messageFor } from '@/lib/errors'
import { secondsSince, formatDuration } from '@/lib/format'

import { MODE_LABEL, STATUS_CHIP, STATUS_LABEL } from './labels'

const router = useRouter()
const machines = ref<MachineOut[]>([])
const labs = ref<LabOut[]>([])
const activeSessions = ref(0)
const error = ref<string | null>(null)
const search = ref('')
const labFilter = ref('')

const showLabForm = ref(false)
const labForm = reactive({ name: '', building: '' })
const labError = ref<string | null>(null)

const machineForm = reactive({ code: '', labId: '', mode: 'passive' as 'passive' | 'kiosk' })
const machineError = ref<string | null>(null)
const creating = ref(false)

const filtered = computed(() =>
  machines.value.filter(
    (m) =>
      m.code.toLowerCase().includes(search.value.trim().toLowerCase()) &&
      (!labFilter.value || m.lab_id === labFilter.value),
  ),
)
const onlineCount = computed(() => machines.value.filter((m) => m.online).length)
const pendingCount = computed(
  () => machines.value.filter((m) => m.status === 'pending_enrollment').length,
)

function lastSeen(machine: MachineOut): string {
  if (machine.online) return 'En línea'
  if (!machine.last_seen_at) return '—'
  return `Hace ${formatDuration(secondsSince(machine.last_seen_at))}`
}

async function load(): Promise<void> {
  error.value = null
  try {
    const [m, l, s] = await Promise.all([
      adminApi.machines(),
      adminApi.labs(),
      adminApi.sessions({ active: true, limit: 200 }),
    ])
    machines.value = m
    labs.value = l
    activeSessions.value = s.items.length
    if (!machineForm.labId && l[0]) machineForm.labId = l[0].id
  } catch (e) {
    error.value = messageFor(e)
  }
}

async function createLab(): Promise<void> {
  labError.value = null
  if (labForm.name.trim().length < 2) {
    labError.value = 'Escribe el nombre de la sala.'
    return
  }
  try {
    const lab = await adminApi.createLab({
      name: labForm.name.trim(),
      building: labForm.building.trim() || null,
    })
    labs.value = [...labs.value, lab].sort((a, b) => a.name.localeCompare(b.name))
    machineForm.labId = lab.id
    labForm.name = ''
    labForm.building = ''
    showLabForm.value = false
  } catch (e) {
    labError.value = messageFor(e)
  }
}

async function createMachine(): Promise<void> {
  machineError.value = null
  if (!/^[A-Za-z0-9_-]{2,40}$/.test(machineForm.code.trim())) {
    machineError.value = 'Usa solo letras, números y guiones (por ejemplo, LAB3-PC14).'
    return
  }
  creating.value = true
  try {
    const machine = await adminApi.createMachine({
      code: machineForm.code.trim(),
      lab_id: machineForm.labId || null,
      mode: machineForm.mode,
    })
    await router.push({ name: 'admin-machine', params: { id: machine.id } })
  } catch (e) {
    machineError.value = messageFor(e)
  } finally {
    creating.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <AdminShell>
    <div class="head">
      <div>
        <h1>Salas y equipos</h1>
        <p class="muted">
          Da de alta los equipos, genera su código de enrolamiento y elige su modo.
        </p>
      </div>
      <button type="button" class="btn btn-outline" @click="showLabForm = !showLabForm">
        Nueva sala
      </button>
    </div>

    <form v-if="showLabForm" class="card lab-form" novalidate @submit.prevent="createLab">
      <div class="field">
        <label for="lab-nombre">Nombre de la sala</label>
        <input id="lab-nombre" v-model="labForm.name" class="input input-sm" placeholder="Sala 3" />
      </div>
      <div class="field">
        <label for="lab-bloque">Bloque o edificio (opcional)</label>
        <input
          id="lab-bloque"
          v-model="labForm.building"
          class="input input-sm"
          placeholder="Bloque B"
        />
      </div>
      <button type="submit" class="btn btn-primary">Crear sala</button>
      <p v-if="labError" class="alert alert-error lab-error" role="alert">{{ labError }}</p>
    </form>

    <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>

    <div class="stats">
      <div class="card stat">
        <span>Equipos</span><strong>{{ machines.length }}</strong>
      </div>
      <div class="card stat">
        <span>En línea ahora</span><strong class="ok">{{ onlineCount }}</strong>
      </div>
      <div class="card stat">
        <span>Sesiones activas</span><strong>{{ activeSessions }}</strong>
      </div>
      <div class="card stat">
        <span>Pendientes de enrolar</span><strong class="info">{{ pendingCount }}</strong>
      </div>
    </div>

    <div class="columns">
      <section class="card list" aria-labelledby="equipos-titulo">
        <div class="toolbar">
          <h2 id="equipos-titulo">Equipos</h2>
          <label for="buscar" class="sr-only">Buscar equipo</label>
          <input
            id="buscar"
            v-model="search"
            class="input input-sm search"
            type="search"
            placeholder="Buscar por código"
          />
          <label for="filtro-sala" class="sr-only">Filtrar por sala</label>
          <select id="filtro-sala" v-model="labFilter" class="input input-sm select">
            <option value="">Todas las salas</option>
            <option v-for="lab in labs" :key="lab.id" :value="lab.id">{{ lab.name }}</option>
          </select>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Equipo</th>
                <th scope="col">Sala</th>
                <th scope="col">Estado</th>
                <th scope="col">Conexión</th>
                <th scope="col">Modo</th>
                <th scope="col"><span class="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in filtered" :key="m.id">
                <td class="mono strong">{{ m.code }}</td>
                <td>{{ m.lab ?? '—' }}</td>
                <td>
                  <span class="chip" :class="STATUS_CHIP[m.status]">{{
                    STATUS_LABEL[m.status]
                  }}</span>
                </td>
                <td :class="{ muted: !m.online }">
                  <span class="conn"
                    ><span class="dot" :class="{ 'dot-off': !m.online }" />{{ lastSeen(m) }}</span
                  >
                </td>
                <td>{{ MODE_LABEL[m.mode] }}</td>
                <td class="right">
                  <RouterLink :to="{ name: 'admin-machine', params: { id: m.id } }" class="strong">
                    Ver
                  </RouterLink>
                </td>
              </tr>
              <tr v-if="!filtered.length">
                <td colspan="6" class="muted empty">No hay equipos que coincidan.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card side" aria-labelledby="nuevo-titulo">
        <h2 id="nuevo-titulo">Nuevo equipo</h2>
        <form class="form" novalidate @submit.prevent="createMachine">
          <div class="field">
            <label for="n-codigo">Código del equipo</label>
            <input
              id="n-codigo"
              v-model="machineForm.code"
              class="input input-sm mono"
              placeholder="LAB3-PC14"
            />
          </div>
          <div class="field">
            <label for="n-sala">Sala</label>
            <select id="n-sala" v-model="machineForm.labId" class="input input-sm">
              <option value="">Sin sala</option>
              <option v-for="lab in labs" :key="lab.id" :value="lab.id">{{ lab.name }}</option>
            </select>
          </div>
          <fieldset class="modes">
            <legend class="field-label">Modo</legend>
            <label
              for="modo-pasivo"
              class="mode"
              :class="{ selected: machineForm.mode === 'passive' }"
            >
              <input id="modo-pasivo" v-model="machineForm.mode" type="radio" value="passive" />
              <span>
                <strong>Pasivo</strong>
                <span class="hint"
                  >El registro es opcional; el equipo se puede usar sin escanear.</span
                >
              </span>
            </label>
            <label
              for="modo-kiosco"
              class="mode"
              :class="{ selected: machineForm.mode === 'kiosk' }"
            >
              <input id="modo-kiosco" v-model="machineForm.mode" type="radio" value="kiosk" />
              <span>
                <strong>Kiosco</strong>
                <span class="hint"
                  >La pantalla del QR ocupa el equipo hasta que alguien inicie sesión.</span
                >
              </span>
            </label>
          </fieldset>
          <p v-if="machineError" class="alert alert-error" role="alert">{{ machineError }}</p>
          <button type="submit" class="btn btn-primary" :disabled="creating">
            {{ creating ? 'Creando…' : 'Crear equipo' }}
          </button>
          <p class="hint">
            Después de crearlo, genera su código de enrolamiento desde el detalle del equipo.
          </p>
        </form>
      </section>
    </div>
  </AdminShell>
</template>

<style scoped src="./admin.css"></style>
