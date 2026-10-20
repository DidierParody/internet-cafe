<script setup lang="ts">
withDefaults(defineProps<{ size?: number; dark?: boolean; label?: boolean }>(), {
  size: 28,
  dark: false,
  label: true,
})
</script>

<template>
  <span class="brand" :class="{ 'brand-dark': dark }">
    <svg :width="size" :height="size" viewBox="0 0 28 28" aria-hidden="true">
      <rect width="28" height="28" rx="8" :fill="dark ? '#3B66E6' : '#1F4FD1'" />
      <rect x="7" y="7" width="6" height="6" rx="1.5" fill="#fff" />
      <rect x="15" y="7" width="6" height="6" rx="1.5" fill="#fff" opacity=".55" />
      <rect x="7" y="15" width="6" height="6" rx="1.5" fill="#fff" opacity=".55" />
      <rect x="15" y="15" width="6" height="6" rx="1.5" fill="#fff" />
    </svg>
    <span v-if="label" class="brand-name">AccesoLab</span>
  </span>
</template>

<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  gap: 9px;
}
.brand-name {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.brand-dark .brand-name {
  color: #fff;
  font-size: 17px;
}
</style>
