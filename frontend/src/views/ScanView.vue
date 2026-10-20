<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { type DetectedBarcode, QrcodeStream, setZXingModuleOverrides } from 'vue-qrcode-reader'
import { useRouter } from 'vue-router'
import wasmUrl from 'zxing-wasm/reader/zxing_reader.wasm?url'

import AppIcon from '@/components/AppIcon.vue'
import MobileShell from '@/components/MobileShell.vue'
import { tokenFromQrText } from '@/lib/scanUrl'
import { useScanStore } from '@/stores/scan'

// El lector carga su .wasm desde nuestro propio dominio (no desde un CDN): así cumple la CSP.
setZXingModuleOverrides({
  locateFile: (path: string, prefix: string) => (path.endsWith('.wasm') ? wasmUrl : prefix + path),
})

type State = 'checking' | 'permiso' | 'camara' | 'denegado' | 'sin-camara' | 'error'

const router = useRouter()
const scan = useScanStore()
const state = ref<State>('checking')
const notice = ref<string | null>(null)
const errorText = ref('')

onMounted(async () => {
  try {
    const status = await navigator.permissions?.query({ name: 'camera' as PermissionName })
    state.value =
      status?.state === 'granted' ? 'camara' : status?.state === 'denied' ? 'denegado' : 'permiso'
  } catch {
    // Safari no permite consultar el permiso de cámara: se pide al tocar el botón.
    state.value = 'permiso'
  }
})

function onError(error: Error): void {
  switch (error.name) {
    case 'NotAllowedError':
      state.value = 'denegado'
      break
    case 'NotFoundError':
    case 'OverconstrainedError':
      state.value = 'sin-camara'
      break
    case 'NotReadableError':
      errorText.value = 'La cámara está en uso por otra aplicación. Ciérrala e inténtalo de nuevo.'
      state.value = 'error'
      break
    case 'InsecureContextError':
    case 'NotSecureContextError':
      errorText.value = 'La cámara solo funciona en una conexión segura (HTTPS).'
      state.value = 'error'
      break
    default:
      errorText.value = 'No pudimos abrir la cámara. Inténtalo de nuevo.'
      state.value = 'error'
  }
}

function onDetect(codes: DetectedBarcode[]): void {
  for (const code of codes) {
    const token = tokenFromQrText(code.rawValue, window.location.origin)
    if (token) {
      scan.set(token)
      void router.push({ name: 'confirm' })
      return
    }
  }
  notice.value = 'Este código no pertenece al sistema. Escanea el QR que muestra el equipo.'
}
</script>

<template>
  <MobileShell :dark="state === 'camara'">
    <template v-if="state === 'camara'">
      <header class="topbar dark">
        <RouterLink to="/" class="icon-btn round" aria-label="Cerrar escáner">
          <AppIcon name="close" :size="22" :stroke="2" />
        </RouterLink>
        <h1 class="title">Escanear QR</h1>
      </header>
      <div class="camera-area">
        <div class="viewport">
          <QrcodeStream
            :constraints="{ facingMode: 'environment' }"
            :formats="['qr_code']"
            @detect="onDetect"
            @error="onError"
          >
            <div class="frame" aria-hidden="true">
              <span class="corner tl" /><span class="corner tr" /><span class="corner bl" /><span
                class="corner br"
              />
              <span class="line" />
            </div>
          </QrcodeStream>
        </div>
        <div class="copy">
          <p class="lead">Apunta al código QR que muestra la pantalla del equipo</p>
          <p class="sub">Mantén el celular quieto: el código se lee solo.</p>
        </div>
        <p v-if="notice" class="notice" role="status">{{ notice }}</p>
      </div>
      <div class="tip">
        <AppIcon name="camera" :size="22" :stroke="1.8" />
        <p>
          ¿Prefieres la cámara de tu celular? Escanea el QR con ella y se abrirá esta página con el
          equipo listo.
        </p>
      </div>
    </template>

    <template v-else>
      <header class="topbar">
        <RouterLink to="/" class="icon-btn" aria-label="Volver al inicio">
          <AppIcon name="back" :stroke="2" />
        </RouterLink>
        <span class="title-light">Escanear QR</span>
      </header>

      <div v-if="state === 'checking'" class="center" aria-busy="true" />

      <template v-else-if="state === 'permiso'">
        <div class="center">
          <div class="badge-icon"><AppIcon name="camera" :size="38" :stroke="1.7" /></div>
          <h1>Necesitamos tu cámara</h1>
          <p>Solo la usamos para leer el código QR del equipo. No guardamos fotos ni video.</p>
        </div>
        <div class="actions">
          <button type="button" class="btn btn-primary btn-lg btn-block" @click="state = 'camara'">
            Permitir cámara
          </button>
          <p class="muted-center">También puedes escanear el QR con la cámara de tu celular.</p>
        </div>
      </template>

      <template v-else>
        <div class="stack">
          <div class="badge-icon warn"><AppIcon name="camera-off" :size="32" :stroke="1.8" /></div>
          <template v-if="state === 'denegado'">
            <h1>La cámara está bloqueada</h1>
            <p>Para escanear desde aquí, permite el acceso a la cámara en tu navegador:</p>
            <ol>
              <li><strong>iPhone (Safari):</strong> Ajustes › Safari › Cámara › Permitir.</li>
              <li>
                <strong>Android (Chrome):</strong> toca el ícono junto a la dirección › Permisos ›
                Cámara.
              </li>
            </ol>
          </template>
          <template v-else-if="state === 'sin-camara'">
            <h1>No encontramos una cámara</h1>
            <p>Este dispositivo no tiene una cámara disponible para escanear.</p>
          </template>
          <template v-else>
            <h1>No pudimos abrir la cámara</h1>
            <p>{{ errorText }}</p>
          </template>
          <div class="alt card">
            <AppIcon name="scan" :size="22" :stroke="1.8" />
            <p>
              <strong>Alternativa:</strong> abre la cámara de tu celular y apunta al QR del equipo.
              Se abrirá esta página con el equipo listo para confirmar.
            </p>
          </div>
        </div>
        <div class="actions">
          <button type="button" class="btn btn-outline btn-lg btn-block" @click="state = 'camara'">
            Intentar de nuevo
          </button>
        </div>
      </template>
    </template>
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
  border-radius: 12px;
  color: var(--ink);
}
.round {
  border-radius: 22px;
  background: #1a2438;
  color: #fff;
}
.title {
  margin-left: 8px;
  font-size: 17px;
  font-weight: 600;
}
.title-light {
  font-size: 16px;
  font-weight: 600;
}
.camera-area {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 28px;
  padding: 0 28px;
}
.viewport {
  width: min(78vw, 300px);
  aspect-ratio: 1;
  border-radius: 24px;
  overflow: hidden;
  background: #111a2c;
}
.frame {
  position: absolute;
  inset: 0;
}
.corner {
  position: absolute;
  width: 48px;
  height: 48px;
  border: 0 solid #fff;
}
.tl {
  left: 0;
  top: 0;
  border-left-width: 4px;
  border-top-width: 4px;
  border-top-left-radius: 22px;
}
.tr {
  right: 0;
  top: 0;
  border-right-width: 4px;
  border-top-width: 4px;
  border-top-right-radius: 22px;
}
.bl {
  left: 0;
  bottom: 0;
  border-left-width: 4px;
  border-bottom-width: 4px;
  border-bottom-left-radius: 22px;
}
.br {
  right: 0;
  bottom: 0;
  border-right-width: 4px;
  border-bottom-width: 4px;
  border-bottom-right-radius: 22px;
}
.line {
  position: absolute;
  left: 28px;
  right: 28px;
  top: 50%;
  height: 2px;
  border-radius: 1px;
  background: #7ea2ff;
}
.copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: center;
}
.lead {
  font-size: 18px;
  line-height: 1.4;
  font-weight: 600;
}
.sub {
  font-size: 14px;
  line-height: 1.5;
  color: #b8c2d6;
}
.notice {
  padding: 10px 14px;
  border-radius: 12px;
  background: #3a2a10;
  color: #fde2b6;
  font-size: 14px;
  text-align: center;
}
.tip {
  margin: 0 20px 28px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 16px;
  border-radius: 16px;
  background: #151f33;
  color: #d5dce8;
  font-size: 14px;
  line-height: 1.5;
}
.center {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 0 32px;
  text-align: center;
}
.badge-icon {
  width: 80px;
  height: 80px;
  border-radius: 24px;
  background: var(--primary-soft);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
}
.badge-icon.warn {
  width: 64px;
  height: 64px;
  border-radius: 20px;
  background: var(--warn-soft);
  color: var(--warn-strong);
}
h1 {
  font-size: 24px;
  line-height: 1.25;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.center p,
.stack > p {
  font-size: 15px;
  line-height: 1.55;
  color: var(--muted);
}
.stack {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px 24px 0;
}
ol {
  margin: 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  font-size: 15px;
  line-height: 1.5;
}
.alt {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 16px;
  color: var(--primary);
  border-radius: 14px;
}
.alt p {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-2);
}
.actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 24px 32px;
}
.muted-center {
  text-align: center;
  font-size: 14px;
  line-height: 1.5;
  color: var(--muted);
}
</style>
