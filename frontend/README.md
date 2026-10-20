# Web · Registro de acceso a equipos por QR (PoC)

Vue 3 + Vite + TypeScript + Pinia + Vue Router. Implementa las 10 pantallas del PoC:

- **Estudiante, mobile-first:** login, registro, inicio, escanear QR, confirmar acceso, historial y perfil.
- **Administración:** salas y equipos, detalle de equipo y accesos.

## Decisiones de implementación

- **Mismo origen:** la app llama a `/api/v1`.
  - En desarrollo, Vite reenvía `/api` a la API local (`VITE_API_PROXY`, por defecto `http://localhost:8000`).
  - En Vercel, `vercel.json` reescribe `/api/*` hacia Render.
  - Así la cookie de refresh es _first-party_ y no hace falta CORS.
- **Tokens:** el access token vive solo en memoria (`src/api/http.ts`); la sesión se recupera al recargar con la cookie HttpOnly de refresh. La renovación se coordina entre pestañas con la Web Locks API.
- **QR:** el token llega en el fragmento (`/s#token`), se guarda en memoria y se borra de la URL. El escáner (`vue-qrcode-reader`) solo acepta QR del propio dominio con la ruta `/s`, y carga su `.wasm` desde el mismo origen para cumplir la CSP.
- **Tipos:** se generan del contrato de la API (`contracts/openapi.json`).

## Comandos

```bash
npm install
npm run dev          # http://localhost:5173 (requiere la API en http://localhost:8000)
npm test             # Vitest
npm run lint         # ESLint + Prettier
npm run type-check   # vue-tsc
npm run build
npm run gen:api      # regenera src/api/schema.d.ts desde ../contracts/openapi.json
```

Para actualizar el contrato después de cambiar la API:

```bash
cd ../backend && uv run python -m app.openapi_export ../contracts/openapi.json
cd ../frontend && npm run gen:api
```

## Despliegue en Vercel

1. Importa el repositorio en Vercel con **Root Directory = `frontend`** (framework Vite). `vercel.json` ya define el build, el rewrite, los headers de seguridad (CSP, Permissions-Policy con cámara solo para el propio sitio y Referrer-Policy) y omite el build si no cambió `frontend/`.
2. Cambia el destino del rewrite `/api/:path*` en `vercel.json` si tu servicio de Render no se llama `internet-cafe-api`.
3. En Render, pon `FRONTEND_BASE_URL` con la URL de Vercel (por ejemplo, `https://internet-cafe.vercel.app`). Es la base del QR y el único origen aceptado para la cookie de refresh.
4. La cámara del navegador solo funciona con HTTPS: en producción Vercel la sirve así; en local, `localhost` cuenta como contexto seguro.
