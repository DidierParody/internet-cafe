<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { meApi, type SessionOut } from '@/api/endpoints'
import MobileShell from '@/components/MobileShell.vue'
import { messageFor } from '@/lib/errors'
import { endReasonLabel, formatDuration, groupByDay, timeHM } from '@/lib/format'

const items = ref<SessionOut[]>([])
const cursor = ref<string | null>(null)
const loading = ref(true)
const loadingMore = ref(false)
const error = ref<string | null>(null)

const groups = computed(() => groupByDay(items.value))

function reasonClass(reason: string | null | undefined): string {
  if (reason === 'heartbeat_timeout') return 'chip-warn'
  if (reason === 'admin_forced') return 'chip-danger'
  return 'chip-neutral'
}

async function load(more = false): Promise<void> {
  error.value = null
  if (more) loadingMore.value = true
  try {
    const page = await meApi.sessions(20, more ? cursor.value : null)
    items.value = more ? [...items.value, ...page.items] : page.items
    cursor.value = page.next_cursor ?? null
  } catch (e) {
    error.value = messageFor(e)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <MobileShell nav>
    <header class="head">
      <h1>Historial</h1>
      <p>Tus accesos a los equipos de la universidad.</p>
    </header>
    <main class="page">
      <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>
      <p v-if="loading" class="muted" aria-busy="true">Cargando tus accesos…</p>
      <p v-else-if="!items.length && !error" class="card empty">
        Aún no tienes accesos registrados. Escanea el QR de un equipo para empezar.
      </p>

      <section v-for="group in groups" :key="group.label" class="group">
        <h2 class="day">{{ group.label }}</h2>
        <article
          v-for="item in group.items"
          :key="item.id"
          class="card entry"
          :class="{ live: item.status === 'active' }"
        >
          <div class="row">
            <span class="mono code">{{ item.machine.code }}</span>
            <span v-if="item.status === 'active'" class="chip chip-success">
              <span class="dot" />En curso
            </span>
            <span v-else class="duration">{{ formatDuration(item.duration_s ?? 0) }}</span>
          </div>
          <div class="row muted small">
            <span>{{ item.machine.lab ?? 'Sin sala' }}</span>
            <span>
              {{ timeHM(item.started_at) }} –
              {{ item.ended_at ? timeHM(item.ended_at) : 'ahora' }}
            </span>
          </div>
          <span v-if="item.end_reason" class="chip reason" :class="reasonClass(item.end_reason)">
            {{ endReasonLabel(item.end_reason) }}
          </span>
        </article>
      </section>

      <button
        v-if="cursor"
        type="button"
        class="btn btn-outline btn-block"
        :disabled="loadingMore"
        @click="load(true)"
      >
        {{ loadingMore ? 'Cargando…' : 'Cargar más' }}
      </button>
    </main>
  </MobileShell>
</template>

<style scoped>
.head {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 20px 20px 12px;
}
h1 {
  font-size: 26px;
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.head p,
.muted {
  color: var(--muted);
  font-size: 15px;
}
.page {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 4px 20px 24px;
}
.empty {
  padding: 20px;
  font-size: 15px;
  line-height: 1.5;
  color: var(--muted);
}
.group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.day {
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.entry {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 14px;
}
.live {
  border-color: #bfe3cf;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.code {
  font-size: 16px;
  font-weight: 600;
}
.duration {
  font-size: 14px;
  font-weight: 600;
}
.small {
  font-size: 14px;
}
.reason {
  align-self: flex-start;
}
</style>
