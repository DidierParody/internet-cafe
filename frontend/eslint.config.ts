import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'

export default defineConfigWithVueTs(
  { name: 'app/archivos', files: ['**/*.{ts,mts,vue}'] },
  { name: 'app/ignorados', ignores: ['dist/**', 'coverage/**', 'src/api/schema.d.ts'] },
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
  skipFormatting,
)
