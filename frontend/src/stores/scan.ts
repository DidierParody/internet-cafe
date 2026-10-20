import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Token del QR escaneado. Vive solo en memoria (sin storage) para sobrevivir al login
 * intermedio sin recargar la página (RF-QR-05).
 */
export const useScanStore = defineStore('scan', () => {
  const token = ref<string | null>(null)

  function set(value: string): void {
    token.value = value
  }

  function clear(): void {
    token.value = null
  }

  return { token, set, clear }
})
