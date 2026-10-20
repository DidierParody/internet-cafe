<script setup lang="ts">
import { useRouter } from 'vue-router'

import { initials } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'

import AppIcon from './AppIcon.vue'
import BrandMark from './BrandMark.vue'

const auth = useAuthStore()
const router = useRouter()

async function logout(): Promise<void> {
  await auth.logout()
  await router.push({ name: 'login' })
}
</script>

<template>
  <div class="admin">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <BrandMark dark />
        <span class="badge">Admin</span>
      </div>
      <nav aria-label="Administración" class="sidebar-nav">
        <RouterLink :to="{ name: 'admin-machines' }" class="nav-item" active-class="nav-active">
          <AppIcon name="monitor" :size="20" />Salas y equipos
        </RouterLink>
        <RouterLink :to="{ name: 'admin-sessions' }" class="nav-item" active-class="nav-active">
          <AppIcon name="history" :size="20" />Accesos
        </RouterLink>
      </nav>
      <div class="spacer" />
      <div class="account">
        <div class="avatar" aria-hidden="true">{{ initials(auth.user?.full_name ?? '') }}</div>
        <div class="account-text">
          <span class="account-name">{{ auth.user?.full_name }}</span>
          <button type="button" class="link-button" @click="logout">Cerrar sesión</button>
        </div>
      </div>
    </aside>
    <main class="content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.admin {
  min-height: 100vh;
  display: flex;
  flex-wrap: wrap;
  background: var(--bg);
}
.sidebar {
  flex: 1 1 232px;
  max-width: 100%;
  padding: 24px 16px;
  background: var(--navy);
  color: #fff;
  display: flex;
  flex-direction: column;
  gap: 28px;
}
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px;
}
.badge {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--navy-2);
  color: var(--navy-text);
  font-size: 11px;
  font-weight: 600;
}
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 0 12px;
  border-radius: 10px;
  color: var(--navy-text);
  font-size: 15px;
  font-weight: 500;
  text-decoration: none;
}
.nav-item:hover {
  color: #fff;
}
.nav-active {
  background: var(--navy-2);
  color: #fff;
  font-weight: 600;
}
.spacer {
  flex-grow: 1;
}
.account {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 8px 0;
  border-top: 1px solid var(--navy-2);
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  background: #26344f;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}
.account-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.account-name {
  font-size: 14px;
  font-weight: 600;
}
.link-button {
  padding: 0;
  border: 0;
  background: none;
  color: var(--navy-text);
  font-size: 13px;
  text-align: left;
  text-decoration: underline;
  cursor: pointer;
}
.content {
  flex: 999 1 560px;
  min-width: 0;
  padding: 32px 40px 40px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}
@media (max-width: 640px) {
  .content {
    padding: 24px 16px 32px;
  }
}
</style>
