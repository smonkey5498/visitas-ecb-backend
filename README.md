# Visitas ECB — backend

Backend en FastAPI + Supabase para digitalizar el acta de visita a
corresponsales bancarios (PDS) de Atlas Transvalores / Fundación Grupo
Social: búsqueda de PDS, registro de visitas (Prospección, Seguimiento,
Oficina) con GPS, catálogo de preguntas por sección, evidencia
fotográfica, cierre de acta, alertas de PDS con más de 90 días sin
visita y galería de evidencias.

## Estructura

- `app.py` — rutas FastAPI (`/pds`, `/gestores`, `/preguntas`, `/visitas`,
  `/respuestas`, `/evidencias`, `/acta`, `/galeria`, `/alertas/...`).
- `services/` — lógica de negocio por dominio (pds, gestores, preguntas,
  visitas, evidencias, alertas, db).
- `templates/` + `static/` — el formulario del acta (`/acta`) y la
  galería de evidencias (`/galeria`), pensados para celular.
- `scripts/enviar_alertas.py` — envía por correo (Resend) la lista de
  PDS con más de 90 días sin visita a cada gestor; se ejecuta por
  cron desde GitHub Actions (`.github/workflows/alertas.yml`).
- `migrar_preguntas_csv.py` — carga/actualiza el catálogo de 104
  preguntas (`PREGUNTAS_VISITA_consolidado.csv`) en Supabase.
- `migrar_datos.py` — carga inicial del portafolio de PDS y gestores.
- `schema.sql` — esquema de las tablas en Supabase (Postgres).

## Configuración local (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# copia .env.example (si no existe .env) y completa las variables
# (Supabase, Resend) — ver la sección "Variables de entorno" abajo

uvicorn app:app --reload
```

Abre `http://127.0.0.1:8000/acta` en el navegador (o desde el celular,
si el celular está en la misma red, usando la IP del computador).

## Variables de entorno

| Variable | Para qué |
|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Conexión a Supabase (Project Settings → API) |
| `TABLE_PDS`, `TABLE_GESTORES`, `TABLE_PREGUNTAS`, `TABLE_ACTAS`, `TABLE_RESPUESTAS`, `TABLE_EVIDENCIAS`, `TABLE_CAMBIOS` | Nombres de tabla (coinciden con `schema.sql`) |
| `BUCKET_EVIDENCIAS` | Bucket de Supabase Storage para las fotos (debe estar marcado como público) |
| `RESEND_API_KEY`, `RESEND_FROM` | Envío de alertas por correo (resend.com) |
| `RESEND_OVERRIDE_TO` | (Opcional, modo prueba) redirige todos los correos de alerta a esta dirección en vez de al gestor real |

`.env` nunca se sube al repositorio (está en `.gitignore`); en Render,
estas variables se configuran en el panel del servicio.

## Publicar en Render

1. Sube este repositorio a GitHub (ver más abajo).
2. En [render.com](https://render.com), **New → Web Service** y conecta
   el repositorio.
3. Render detecta `render.yaml` y preconfigura el servicio; solo falta
   completar los valores de las variables de entorno marcadas como
   secretas (usa los mismos valores de tu `.env` local).
4. Cuando termine el primer deploy, la URL pública (algo como
   `https://visitas-ecb-backend.onrender.com`) queda lista — `/acta` y
   `/galeria` funcionan desde cualquier celular, sin depender de que un
   computador esté encendido.

## Alertas semanales (GitHub Actions)

`.github/workflows/alertas.yml` corre `scripts/enviar_alertas.py` cada
lunes. Para que funcione, el repositorio en GitHub necesita estos
Secrets (Settings → Secrets and variables → Actions): `SUPABASE_URL`,
`SUPABASE_SERVICE_KEY`, `RESEND_API_KEY`, `RESEND_FROM` (y
`RESEND_OVERRIDE_TO` mientras se siga en modo prueba).
