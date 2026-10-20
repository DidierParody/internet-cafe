import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { authApi, type UserSummary } from '@/api/endpoints'
import { onSessionExpired, refreshAccessToken, setAccessToken } from '@/api/http'

/** Sesión web. Solo guarda nombre y rol; el access token vive en api/http.ts. */
export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserSummary | null>(null)
  const ready = ref(false)
  let bootstrapping: Promise<void> | null = null

  const authenticated = computed(() => user.value !== null)
  const role = computed(() =>
    user.value?.role === 'admin' ? 'admin' : user.value ? 'student' : null,
  )
  const firstName = computed(() => user.value?.full_name.split(/\s+/)[0] ?? '')

  onSessionExpired(() => {
    user.value = null
  })

  /** Al cargar la página: recupera la sesión con la cookie de refresh, si existe. */
  function bootstrap(): Promise<void> {
    if (ready.value) return Promise.resolve()
    bootstrapping ??= refreshAccessToken()
      .then((tokens) => {
        user.value = tokens?.user ?? null
      })
      .catch(() => {
        user.value = null
      })
      .finally(() => {
        ready.value = true
      })
    return bootstrapping
  }

  async function login(email: string, password: string): Promise<void> {
    const tokens = await authApi.login({ email, password })
    setAccessToken(tokens.access_token)
    user.value = tokens.user
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } finally {
      setAccessToken(null)
      user.value = null
    }
  }

  return { user, ready, authenticated, role, firstName, bootstrap, login, logout }
})
