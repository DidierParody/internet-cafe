<script setup lang="ts">
import { ICON_PATHS, type IconName } from './icons'

// Íconos decorativos: el texto accesible lo pone el control que los contiene.
const props = withDefaults(defineProps<{ name: IconName; size?: number; stroke?: number }>(), {
  size: 24,
  stroke: 1.9,
})
</script>

<template>
  <svg
    :width="props.size"
    :height="props.size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="props.stroke"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path v-for="d in ICON_PATHS[props.name]" :key="d" :d="d" />
  </svg>
</template>

<style scoped>
/* Dentro de una fila flex con texto largo, el ícono conserva su tamaño. */
svg {
  flex-shrink: 0;
}
</style>
