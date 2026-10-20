<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import type { IconName } from './icons'

const items: { to: string; label: string; icon: IconName }[] = [
  { to: '/', label: 'Inicio', icon: 'home' },
  { to: '/escanear', label: 'Escanear', icon: 'scan' },
  { to: '/historial', label: 'Historial', icon: 'history' },
  { to: '/perfil', label: 'Perfil', icon: 'user' },
]
</script>

<template>
  <nav class="bottom-nav" aria-label="Principal">
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="tab"
      exact-active-class="tab-active"
    >
      <AppIcon :name="item.icon" :stroke="2" />
      {{ item.label }}
    </RouterLink>
  </nav>
</template>

<style scoped>
.bottom-nav {
  position: sticky;
  bottom: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  min-height: 68px;
  padding-bottom: env(safe-area-inset-bottom, 0);
  background: var(--surface);
  border-top: 1px solid var(--border);
}
.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 60px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
}
.tab:hover {
  color: var(--ink);
}
.tab-active,
.tab-active:hover {
  color: var(--primary);
  font-weight: 700;
}
</style>
