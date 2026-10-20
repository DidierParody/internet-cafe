<script setup lang="ts">
import BottomNav from './BottomNav.vue'

// Columna de ancho de celular, centrada en pantallas grandes.
withDefaults(defineProps<{ nav?: boolean; dark?: boolean }>(), { nav: false, dark: false })
</script>

<template>
  <div class="shell" :class="{ 'shell-dark': dark }">
    <div class="column">
      <slot />
      <BottomNav v-if="nav" />
    </div>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  justify-content: center;
  background: #e9edf4;
}
.column {
  width: 100%;
  max-width: 480px;
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}
.shell-dark,
.shell-dark .column {
  background: #0b1220;
  color: #fff;
}
</style>
