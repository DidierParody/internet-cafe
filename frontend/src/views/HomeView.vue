<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { meApi, type SessionOut } from '@/api/endpoints'
import AppIcon from '@/components/AppIcon.vue'
import BrandMark from '@/components/BrandMark.vue'
import MobileShell from '@/components/MobileShell.vue'
import { messageFor } from '@/lib/errors'
import { dayLabel, formatDuration, initials, secondsSince, timeHM } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const active = ref<SessionOut | null>(null)
const recent = ref<SessionOut[]>([])
const loading = ref(true)
const ending = ref(false)
const error = ref<string | null>(null)
const now = ref(new Date())
let timer: ReturnType<typeof setInterval> | undefined

const elapsed = computed(() =>
  active.value ? formatDuration(secondsSince(active.value.started_at, now.value)) : '',
)

async function load(): Promise<void> {
  error.value = null
  try {
    const [current, page] = await Promise.all([meApi.activeSession(), meApi.sessions(4)])
    active.value = current.session ?? null
    recent.value = page.items.filter((s) => s.status === 'ended').slice(0, 3)
  } catch (e) {
    error.value = messageFor(e)
  } finally {
    loading.value = false
  }
}

async function endSession(): Promise<void> {
  if (!active.value) return
  ending.value = true
  try {
    await meApi.endSession(active.value.id)
    await load()
  } catch (e) {
    error.value = messageFor(e)
  } finally {
    ending.value = false
  }
}

onMounted(() => {
  void load()
  timer = setInterval(() => (now.value = new Date()), 30_000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <MobileShell nav>
    <header class="topbar">
      <BrandMark :size="26" />
      <RouterLink
        to="/perfil"
        class="avatar"
        :aria-label="`Perfil de ${auth.user?.full_name ?? ''}`"
      >
        {{ initials(auth.user?.full_name ?? '') }}
      </RouterLink>
    </header>
    <main class="page">
      <div class="greeting">
        <h1>Hola, {{ auth.firstName }}</h1>
        <p>¿En qué equipo vas a trabajar hoy?</p>
      </div>

      <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>

      <section v-if="loading" class="card skeleton" aria-busy="true" aria-label="Cargando" />

      <section v-else-if="active" class="card session" aria-labelledby="sesion-titulo">
        <div class="row-between">
          <h2 id="sesion-titulo" class="eyebrow">Sesión en curso</h2>
          <span class="chip chip-success"><span class="dot" />Activa</span>
        </div>
        <div class="machine">
          <div class="machine-icon"><AppIcon name="monitor" :size="26" :stroke="1.8" /></div>
          <div class="machine-text">
            <span class="mono machine-code">{{ active.machine.code }}</span>
            <span class="muted">{{ active.machine.lab ?? 'Sin sala' }}</span>
          </div>
        </div>
        <div class="stats">
          <div class="stat">
            <span>Inicio</span><strong>{{ timeHM(active.started_at) }}</strong>
          </div>
          <div class="stat">
            <span>Tiempo</span><strong>{{ elapsed }}</strong>
          </div>
        </div>
        <button type="button" class="btn btn-danger" :disabled="ending" @click="endSession">
          {{ ending ? 'Cerrando…' : 'Cerrar sesión en el equipo' }}
        </button>
      </section>

      <section v-else class="card empty">
        <div class="empty-icon"><AppIcon name="monitor" :size="28" :stroke="1.8" /></div>
        <h2>No tienes una sesión activa</h2>
        <p>Escanea el código QR que muestra la pantalla del equipo para empezar.</p>
      </section>

      <RouterLink to="/escanear" class="btn btn-primary btn-lg scan">
        <AppIcon name="scan" :size="22" :stroke="2" />
        Escanear QR del equipo
      </RouterLink>

      <section v-if="recent.length" aria-labelledby="ultimos-titulo" class="recent">
        <div class="row-between">
          <h2 id="ultimos-titulo" class="section-title">Últimos accesos</h2>
          <RouterLink to="/historial" class="see-all">Ver todo</RouterLink>
        </div>
        <ul class="card list">
          <li v-for="item in recent" :key="item.id">
            <div class="col">
              <span class="mono strong">{{ item.machine.code }}</span>
              <span class="muted small">{{ item.machine.lab ?? 'Sin sala' }}</span>
            </div>
            <div class="col end">
              <span class="strong small-14">{{ dayLabel(new Date(item.started_at)) }}</span>
              <span class="muted small">{{ formatDuration(item.duration_s ?? 0) }}</span>
            </div>
          </li>
        </ul>
      </section>
    </main>
  </MobileShell>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 16px 0 20px;
}
.avatar {
  width: 44px;
  height: 44px;
  border-radius: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--avatar);
  color: var(--primary-hover);
  font-size: 15px;
  font-weight: 700;
  text-decoration: none;
}
.page {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 4px 20px 24px;
}
.greeting {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
h1 {
  font-size: 26px;
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.greeting p,
.muted {
  color: var(--muted);
}
.greeting p {
  font-size: 15px;
}
.row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.eyebrow {
  font-size: 14px;
  font-weight: 600;
  color: var(--muted);
}
.session {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
}
.machine {
  display: flex;
  gap: 14px;
  align-items: center;
}
.machine-icon,
.empty-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.machine-icon {
  background: var(--primary-soft);
  color: var(--primary);
}
.machine-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 14px;
}
.machine-code {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.stat {
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--bg);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat span {
  font-size: 12px;
  color: var(--muted);
}
.stat strong {
  font-size: 16px;
  font-weight: 600;
}
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 28px 20px;
  border-style: dashed;
  border-color: var(--input-border);
  text-align: center;
}
.empty-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: var(--bg);
  color: var(--muted);
}
.empty h2 {
  font-size: 17px;
  font-weight: 700;
}
.empty p {
  font-size: 14px;
  line-height: 1.5;
  color: var(--muted);
}
.skeleton {
  height: 236px;
  background: linear-gradient(90deg, #fff 0%, #f4f6fa 50%, #fff 100%) 0 0 / 200% 100%;
  animation: shimmer 1.2s infinite linear;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
  }
}
.scan {
  min-height: 58px;
  border-radius: 14px;
}
.recent {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.section-title {
  font-size: 17px;
  font-weight: 700;
}
.see-all {
  padding: 10px 0;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
}
.list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
}
.list li + li {
  border-top: 1px solid var(--divider);
}
.col {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.end {
  align-items: flex-end;
}
.strong {
  font-weight: 600;
  font-size: 15px;
}
.small {
  font-size: 13px;
}
.small-14 {
  font-size: 14px;
}
</style>
