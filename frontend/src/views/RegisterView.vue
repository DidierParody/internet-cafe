<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { authApi } from '@/api/endpoints'
import AppIcon from '@/components/AppIcon.vue'
import MobileShell from '@/components/MobileShell.vue'
import { errorCode, messageFor } from '@/lib/errors'
import { useAuthStore } from '@/stores/auth'
import { useScanStore } from '@/stores/scan'

const auth = useAuthStore()
const scan = useScanStore()
const route = useRoute()
const router = useRouter()

const form = reactive({ email: '', code: '', name: '', password: '', consent: false })
const touched = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)

const passwordTooShort = computed(() => form.password.length > 0 && form.password.length < 10)
const missing = computed(
  () => !form.email.trim() || !form.code.trim() || form.name.trim().length < 2 || !form.consent,
)

async function submit(): Promise<void> {
  touched.value = true
  error.value = null
  if (missing.value || form.password.length < 10) {
    error.value = 'Completa todos los campos y acepta el tratamiento de datos.'
    return
  }
  loading.value = true
  try {
    await authApi.register({
      email: form.email.trim(),
      student_code: form.code.trim(),
      full_name: form.name.trim(),
      password: form.password,
      privacy_consent: true,
    })
    await auth.login(form.email.trim(), form.password)
    const next = typeof route.query.next === 'string' ? route.query.next : null
    await router.replace(next ?? (scan.token ? '/s' : '/'))
  } catch (e) {
    // El registro responde 202 aunque el correo o el código ya existan (no revela cuentas):
    // si el login falla después, lo más probable es que la cuenta ya existiera.
    error.value =
      errorCode(e) === 'AUTH_INVALID_CREDENTIALS'
        ? 'No pudimos crear la cuenta con esos datos. Si ya tienes una, inicia sesión.'
        : messageFor(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <MobileShell>
    <header class="topbar">
      <RouterLink
        :to="{ name: 'login', query: route.query }"
        class="icon-link"
        aria-label="Volver al inicio de sesión"
      >
        <AppIcon name="back" :stroke="2" />
      </RouterLink>
      <span>Crear cuenta</span>
    </header>
    <div class="page">
      <div class="intro">
        <h1>Crea tu cuenta</h1>
        <p>La usarás para registrar tu acceso en cualquier equipo de la sala.</p>
      </div>
      <form class="form" novalidate @submit.prevent="submit">
        <div class="field">
          <label for="r-correo">Correo institucional</label>
          <input
            id="r-correo"
            v-model="form.email"
            class="input"
            type="email"
            autocomplete="email"
            placeholder="nombre@universidad.edu.co"
            :aria-invalid="touched && !form.email.trim()"
          />
        </div>
        <div class="field">
          <label for="r-codigo">Código estudiantil</label>
          <input
            id="r-codigo"
            v-model="form.code"
            class="input mono"
            type="text"
            inputmode="numeric"
            autocomplete="off"
            placeholder="2021001234"
            :aria-invalid="touched && !form.code.trim()"
          />
        </div>
        <div class="field">
          <label for="r-nombre">Nombre completo</label>
          <input
            id="r-nombre"
            v-model="form.name"
            class="input"
            type="text"
            autocomplete="name"
            placeholder="Como aparece en tu carné"
            :aria-invalid="touched && form.name.trim().length < 2"
          />
        </div>
        <div class="field">
          <label for="r-clave">Contraseña</label>
          <input
            id="r-clave"
            v-model="form.password"
            class="input"
            type="password"
            autocomplete="new-password"
            aria-describedby="r-clave-ayuda"
            :aria-invalid="passwordTooShort || (touched && form.password.length < 10)"
          />
          <span id="r-clave-ayuda" class="hint">Mínimo 10 caracteres.</span>
        </div>
        <label for="r-consentimiento" class="consent">
          <input id="r-consentimiento" v-model="form.consent" type="checkbox" />
          <span>
            Acepto el tratamiento de mis datos personales según el aviso de privacidad de la
            universidad.
          </span>
        </label>

        <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>

        <button type="submit" class="btn btn-primary btn-lg btn-block" :disabled="loading">
          {{ loading ? 'Creando cuenta…' : 'Crear cuenta' }}
        </button>
      </form>
      <p class="switch">
        ¿Ya tienes cuenta?
        <RouterLink :to="{ name: 'login', query: route.query }">Inicia sesión</RouterLink>
      </p>
    </div>
  </MobileShell>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 60px;
  padding: 0 12px;
  font-size: 16px;
  font-weight: 600;
}
.icon-link {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  color: var(--ink);
}
.page {
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 8px 24px 28px;
}
.intro {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
h1 {
  font-size: 26px;
  line-height: 1.2;
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
  gap: 16px;
}
.consent {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-2);
  cursor: pointer;
}
.consent input {
  width: 22px;
  height: 22px;
  margin: 0;
  flex-shrink: 0;
  accent-color: var(--primary);
}
.switch {
  text-align: center;
  font-size: 15px;
  color: var(--muted);
}
.switch a {
  font-weight: 600;
}
</style>
