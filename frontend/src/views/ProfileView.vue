<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { meApi, type MeOut } from '@/api/endpoints'
import AppIcon from '@/components/AppIcon.vue'
import MobileShell from '@/components/MobileShell.vue'
import { errorCode, messageFor } from '@/lib/errors'
import { initials } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const me = ref<MeOut | null>(null)
const error = ref<string | null>(null)
const pwd = reactive({ current: '', next: '' })
const saving = ref(false)
const pwdMessage = ref<{ ok: boolean; text: string } | null>(null)

const memberSince = (iso: string) =>
  new Intl.DateTimeFormat('es', { month: 'long', year: 'numeric' }).format(new Date(iso))

onMounted(async () => {
  try {
    me.value = await meApi.get()
  } catch (e) {
    error.value = messageFor(e)
  }
})

async function changePassword(): Promise<void> {
  pwdMessage.value = null
  if (pwd.next.length < 10) {
    pwdMessage.value = { ok: false, text: 'La nueva contraseña debe tener al menos 10 caracteres.' }
    return
  }
  saving.value = true
  try {
    await meApi.changePassword({ current_password: pwd.current, new_password: pwd.next })
    // El cambio revoca las sesiones web: se vuelve a iniciar sesión con la clave nueva.
    if (me.value) await auth.login(me.value.email, pwd.next)
    pwd.current = ''
    pwd.next = ''
    pwdMessage.value = { ok: true, text: 'Contraseña actualizada.' }
  } catch (e) {
    pwdMessage.value = {
      ok: false,
      text:
        errorCode(e) === 'AUTH_INVALID_CREDENTIALS'
          ? 'La contraseña actual no es correcta.'
          : messageFor(e),
    }
  } finally {
    saving.value = false
  }
}

async function logout(): Promise<void> {
  await auth.logout()
  await router.push({ name: 'login' })
}
</script>

<template>
  <MobileShell nav>
    <header class="head"><h1>Perfil</h1></header>
    <main class="page">
      <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>
      <section v-if="me" class="card block" aria-label="Tus datos">
        <div class="identity">
          <div class="avatar" aria-hidden="true">{{ initials(me.full_name) }}</div>
          <div class="who">
            <span class="name">{{ me.full_name }}</span>
            <span class="muted">{{ me.email }}</span>
          </div>
        </div>
        <dl>
          <div>
            <dt>Código estudiantil</dt>
            <dd class="mono strong">{{ me.student_code_masked ?? '—' }}</dd>
          </div>
          <div>
            <dt>Rol</dt>
            <dd>
              <span class="chip chip-info">{{
                me.role === 'admin' ? 'Administrador' : 'Estudiante'
              }}</span>
            </dd>
          </div>
          <div>
            <dt>Miembro desde</dt>
            <dd class="strong-500">{{ memberSince(me.created_at) }}</dd>
          </div>
        </dl>
      </section>

      <section class="card block" aria-labelledby="clave-titulo">
        <h2 id="clave-titulo">Cambiar contraseña</h2>
        <form class="form" novalidate @submit.prevent="changePassword">
          <div class="field">
            <label for="p-actual">Contraseña actual</label>
            <input
              id="p-actual"
              v-model="pwd.current"
              class="input"
              type="password"
              autocomplete="current-password"
            />
          </div>
          <div class="field">
            <label for="p-nueva">Nueva contraseña</label>
            <input
              id="p-nueva"
              v-model="pwd.next"
              class="input"
              type="password"
              autocomplete="new-password"
              aria-describedby="p-nueva-ayuda"
            />
            <span id="p-nueva-ayuda" class="hint">
              Mínimo 10 caracteres. Al cambiarla se cierra tu sesión en otros dispositivos.
            </span>
          </div>
          <p
            v-if="pwdMessage"
            class="alert"
            :class="pwdMessage.ok ? 'alert-success' : 'alert-error'"
            role="status"
          >
            {{ pwdMessage.text }}
          </p>
          <button type="submit" class="btn btn-outline-primary" :disabled="saving">
            {{ saving ? 'Actualizando…' : 'Actualizar contraseña' }}
          </button>
        </form>
      </section>

      <button type="button" class="btn btn-danger logout" @click="logout">
        <AppIcon name="logout" :size="20" :stroke="2" />Cerrar sesión
      </button>
    </main>
  </MobileShell>
</template>

<style scoped>
.head {
  padding: 20px 20px 12px;
}
h1 {
  font-size: 26px;
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.page {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 4px 20px 24px;
}
.block {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
}
.identity {
  display: flex;
  align-items: center;
  gap: 14px;
}
.avatar {
  width: 60px;
  height: 60px;
  border-radius: 30px;
  background: var(--avatar);
  color: var(--primary-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  flex-shrink: 0;
}
.who {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  overflow-wrap: anywhere;
}
.name {
  font-size: 19px;
  font-weight: 700;
}
.muted {
  font-size: 14px;
  color: var(--muted);
}
dl {
  margin: 0;
}
dl > div {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-top: 1px solid var(--divider);
}
dl > div:last-child {
  padding-bottom: 0;
}
dt {
  font-size: 14px;
  color: var(--muted);
}
dd {
  margin: 0;
}
.strong {
  font-size: 15px;
  font-weight: 600;
}
.strong-500 {
  font-size: 15px;
  font-weight: 500;
}
h2 {
  font-size: 17px;
  font-weight: 700;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.logout {
  min-height: 50px;
}
</style>
