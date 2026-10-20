<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { type PreviewOut, scanApi, type SessionOut } from '@/api/endpoints'
import AppIcon from '@/components/AppIcon.vue'
import MobileShell from '@/components/MobileShell.vue'
import { errorCode, messageFor } from '@/lib/errors'
import { timeHM } from '@/lib/format'
import { useScanStore } from '@/stores/scan'

type State =
  | 'cargando'
  | 'confirmar'
  | 'exito'
  | 'expirado'
  | 'usado'
  | 'invalido'
  | 'deshabilitado'
  | 'ocupado'
  | 'error'

const ERROR_STATES: Record<string, State> = {
  CHALLENGE_EXPIRED: 'expirado',
  CHALLENGE_ALREADY_USED: 'usado',
  CHALLENGE_NOT_FOUND: 'invalido',
  MACHINE_DISABLED: 'deshabilitado',
  MACHINE_BUSY: 'ocupado',
}

const scan = useScanStore()
const router = useRouter()
const state = ref<State>('cargando')
const info = ref<PreviewOut | null>(null)
const session = ref<SessionOut | null>(null)
const confirming = ref(false)
const errorText = ref('')
const remaining = ref(0)
let timer: ReturnType<typeof setInterval> | undefined

const countdown = computed(() => {
  const s = Math.max(0, remaining.value)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
})

function fail(error: unknown): void {
  state.value = ERROR_STATES[errorCode(error) ?? ''] ?? 'error'
  errorText.value = messageFor(error)
}

function tick(): void {
  if (!info.value) return
  remaining.value = Math.round((new Date(info.value.expires_at).getTime() - Date.now()) / 1000)
  if (remaining.value <= 0 && state.value === 'confirmar') state.value = 'expirado'
}

async function loadPreview(token: string | null): Promise<void> {
  clearInterval(timer)
  info.value = null
  if (!token) {
    state.value = 'invalido'
    return
  }
  state.value = 'cargando'
  try {
    info.value = await scanApi.preview(token)
    state.value = 'confirmar'
    tick()
    timer = setInterval(tick, 1000)
  } catch (e) {
    fail(e)
  }
}

onMounted(() => loadPreview(scan.token))
// Si se escanea otro QR estando ya en /s, solo cambia el fragmento: la vista no se vuelve
// a montar, así que se recarga la vista previa con el token nuevo.
watch(
  () => scan.token,
  (token) => {
    if (token) void loadPreview(token)
  },
)
onBeforeUnmount(() => clearInterval(timer))

async function confirm(): Promise<void> {
  if (!scan.token) return
  confirming.value = true
  try {
    const result = await scanApi.claim(scan.token)
    session.value = result.session
    scan.clear()
    state.value = 'exito'
  } catch (e) {
    fail(e)
  } finally {
    confirming.value = false
  }
}

function cancel(): void {
  scan.clear()
  void router.push({ name: 'home' })
}
</script>

<template>
  <MobileShell>
    <header class="topbar">
      <button
        type="button"
        class="icon-btn"
        aria-label="Cancelar y volver al inicio"
        @click="cancel"
      >
        <AppIcon name="close" :size="22" :stroke="2" />
      </button>
      <span class="title">Confirmar acceso</span>
    </header>

    <div v-if="state === 'cargando'" class="body center" aria-busy="true">
      <p class="muted">Buscando el equipo…</p>
    </div>

    <div v-else-if="state === 'confirmar' && info" class="body">
      <section class="card machine-card">
        <div class="badge-icon"><AppIcon name="monitor" :size="36" :stroke="1.7" /></div>
        <p class="muted">Vas a iniciar sesión en</p>
        <h1 class="mono code">{{ info.machine.code }}</h1>
        <p class="lab">{{ info.machine.lab ?? 'Sin sala asignada' }}</p>
        <span class="countdown" aria-live="off">
          <AppIcon name="history" :size="16" :stroke="2" />El código vence en {{ countdown }}
        </span>
      </section>
      <div v-if="info.active_session" class="alert alert-warn">
        <AppIcon name="warning" :size="22" />
        <p>
          Tienes una sesión abierta en
          <strong class="mono">{{ info.active_session.machine_code }}</strong
          >. Al confirmar, esa sesión se cerrará.
        </p>
      </div>
      <div class="grow" />
      <button
        type="button"
        class="btn btn-primary btn-lg btn-block tall"
        :disabled="confirming"
        @click="confirm"
      >
        {{ confirming ? 'Confirmando…' : 'Confirmar acceso' }}
      </button>
      <button type="button" class="btn btn-ghost btn-block" @click="cancel">Cancelar</button>
    </div>

    <div v-else-if="state === 'exito' && session" class="body">
      <div class="center">
        <div class="result-icon ok"><AppIcon name="check" :size="44" :stroke="2.2" /></div>
        <h1>¡Listo! Ya puedes usar el equipo</h1>
        <p>
          Tu sesión en <strong class="mono">{{ session.machine.code }}</strong> comenzó a las
          {{ timeHM(session.started_at) }}. Tu nombre ya aparece en la pantalla del equipo.
        </p>
        <p class="small">Recuerda cerrar sesión al terminar.</p>
      </div>
      <RouterLink to="/" class="btn btn-primary btn-lg btn-block tall">Ir al inicio</RouterLink>
    </div>

    <div v-else class="body">
      <div class="center">
        <div class="result-icon" :class="state === 'expirado' ? 'warn' : 'neutral'">
          <AppIcon :name="state === 'expirado' ? 'history' : 'info'" :size="38" :stroke="1.8" />
        </div>
        <template v-if="state === 'expirado'">
          <h1>El código QR expiró</h1>
          <p>El equipo muestra un código nuevo cada 45 segundos. Escanea el que aparece ahora.</p>
        </template>
        <template v-else-if="state === 'usado'">
          <h1>Este código ya se usó</h1>
          <p>Otra persona confirmó este código. Escanea el código nuevo que muestra el equipo.</p>
        </template>
        <template v-else-if="state === 'invalido'">
          <h1>No encontramos el código del equipo</h1>
          <p>Escanea el QR que aparece en la pantalla del equipo.</p>
        </template>
        <template v-else-if="state === 'deshabilitado'">
          <h1>Este equipo está deshabilitado</h1>
          <p>Usa otro equipo o avisa al personal de la sala.</p>
        </template>
        <template v-else-if="state === 'ocupado'">
          <h1>El equipo ya tiene una sesión activa</h1>
          <p>Pide que se cierre la sesión en el equipo y vuelve a escanear.</p>
        </template>
        <template v-else>
          <h1>No pudimos registrar el acceso</h1>
          <p>{{ errorText }}</p>
        </template>
      </div>
      <RouterLink to="/escanear" class="btn btn-primary btn-lg btn-block tall">
        Escanear de nuevo
      </RouterLink>
    </div>
  </MobileShell>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 64px;
  padding: 0 12px;
}
.icon-btn {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--ink);
  cursor: pointer;
}
.title {
  font-size: 16px;
  font-weight: 600;
}
.body {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 12px 20px 28px;
}
.center {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  text-align: center;
}
.center p {
  font-size: 15px;
  line-height: 1.55;
  color: var(--muted);
}
.center .small {
  font-size: 14px;
}
.muted {
  color: var(--muted);
  font-size: 15px;
}
.machine-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 32px 20px 28px;
  border-radius: 20px;
  text-align: center;
}
.badge-icon {
  width: 72px;
  height: 72px;
  margin-bottom: 6px;
  border-radius: 22px;
  background: var(--primary-soft);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
}
.code {
  font-size: 34px;
  line-height: 1.1;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.lab {
  font-size: 16px;
  font-weight: 500;
}
.countdown {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--bg);
  color: var(--text-2);
  font-size: 13px;
  font-weight: 500;
}
h1 {
  font-size: 24px;
  line-height: 1.25;
  font-weight: 700;
}
.result-icon {
  width: 80px;
  height: 80px;
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.result-icon.ok {
  width: 88px;
  height: 88px;
  border-radius: 44px;
  background: var(--success-soft);
  color: #0f7a4b;
}
.result-icon.warn {
  background: var(--warn-soft);
  color: var(--warn-strong);
}
.result-icon.neutral {
  background: #eef1f6;
  color: var(--text-2);
}
.grow {
  flex-grow: 1;
}
.tall {
  min-height: 56px;
  border-radius: 14px;
}
</style>
