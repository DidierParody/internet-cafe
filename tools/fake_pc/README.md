# Simulador del PC (PoC)

Reemplaza a la aplicación de escritorio en el PoC. Ejecuta la dinámica completa del QR contra la API:

1. Enrolamiento con un código del panel admin.
2. QR en la terminal y en `qr-actual.png`, renovado cada 45 s.
3. Long-poll hasta que un estudiante confirma desde el celular.
4. Tablero con el nombre, el código enmascarado y los últimos accesos.
5. Latido cada 60 s; detecta cierres hechos desde la web, el admin u otro equipo.
6. Cierre con Enter (`user_logout_pc`) o al apagar con Ctrl+C (`machine_shutdown`).

No firma peticiones: usa el token del equipo (Bearer). No requiere instalar nada aparte de [uv](https://docs.astral.sh/uv/); las dependencias se declaran en el propio script.

```bash
# 1. En el panel admin (o en /api/docs): crea la sala y el equipo, y genera un código de enrolamiento.
uv run tools/fake_pc/fake_pc.py enroll --api https://<tu-api>.onrender.com --code ABCD-EFGH

# 2. Muestra el QR y atiende sesiones (--open abre el PNG en el visor de imágenes).
uv run tools/fake_pc/fake_pc.py run --open
```

El token del equipo se guarda en `tools/fake_pc/.machine.json`, que está en `.gitignore`.
