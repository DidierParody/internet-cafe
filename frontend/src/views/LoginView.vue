<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import BrandMark from '@/components/BrandMark.vue'
import MobileShell from '@/components/MobileShell.vue'
import { messageFor } from '@/lib/errors'
import { useAuthStore } from '@/stores/auth'
import { useScanStore } from '@/stores/scan'

const auth = useAuthStore()
const scan = useScanStore()
const route = useRoute()
const router = useRouter()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)

function nextPath(): string {
  const next = typeof route.query.next === 'string' ? route.query.next : null
  if (next?.startsWith('/') && !next.startsWith('//')) return next
  if (scan.token) return '/s'
  return auth.role === 'admin' ? '/admin/equipos' : '/'
}

async function submit(): Promise<void> {
  error.value = null
  loading.value = true
  try {
    await auth.login(email.value.trim(), password.value)
    await router.replace(nextPath())
  } catch (e) {
    error.value = messageFor(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <MobileShell>
    <div class="page">
      <BrandMark :size="32" />
      <div class="intro">
        <h1>Inicia sesión</h1>
        <p>Registra tu acceso a los equipos de la sala con tu cuenta institucional.</p>
      </div>

      <div v-if="scan.token" class="alert alert-info">
        <AppIcon name="monitor" :size="22" />
        <p>Escaneaste el QR de un equipo. Inicia sesión para registrar tu acceso.</p>
      </div>

      <form class="form" novalidate @submit.prevent="submit">
        <div class="field">
          <label for="correo">Correo institucional</label>
          <input
            id="correo"
            v-model="email"
            class="input"
            type="email"
            autocomplete="email"
            placeholder="nombre@universidad.edu.co"
            required
          />
        </div>
        <div class="field">
          <label for="clave">Contraseña</label>
          <div class="password">
            <input
              id="clave"
              v-model="password"
              class="input"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              required
            />
            <button
              type="button"
              class="reveal"
              :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              :aria-pressed="showPassword"
              @click="showPassword = !showPassword"
            >
              <AppIcon :name="showPassword ? 'eye-off' : 'eye'" :size="22" />
            </button>
          </div>
        </div>

        <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>

        <button type="submit" class="btn btn-primary btn-lg btn-block" :disabled="loading">
          {{ loading ? 'Ingresando…' : 'Iniciar sesión' }}
        </button>
      </form>

      <p class="switch">
        ¿No tienes cuenta?
        <RouterLink :to="{ name: 'register', query: route.query }">Crea una</RouterLink>
      </p>
      <div class="grow" />
      <p class="footnote">
        Usa el mismo correo y contraseña en todos los equipos de la universidad.
      </p>
    </div>
  </MobileShell>
</template>

<style scoped>
.page {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 56px 24px 32px;
}
.intro {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
h1 {
  font-size: 30px;
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.intro p {
  font-size: 15px;
  line-height: 1.5;
  color: var(--muted);
}
.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.password {
  position: relative;
}
.password .input {
  padding-right: 52px;
}
.reveal {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}
.switch {
  text-align: center;
  font-size: 15px;
  color: var(--muted);
}
.switch a {
  font-weight: 600;
}
.grow {
  flex-grow: 1;
}
.footnote {
  text-align: center;
  font-size: 13px;
  line-height: 1.5;
  color: var(--subtle);
}
</style>
