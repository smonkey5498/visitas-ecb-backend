"""
Envía por correo, a cada gestor, la lista de sus PDS pendientes de
visita (más de DIAS_ALERTA días sin visita completa, o nunca visitados).

Corre por fuera de la API — no necesita que uvicorn esté corriendo.
Lee directo de Supabase (services/db.py) y envía los correos con Resend.

Uso local (para probar):
    python scripts/enviar_alertas.py

Uso programado: ver .github/workflows/alertas.yml — corre solo, una
vez por semana, con GitHub Actions (no depende de tu computador).

Requiere en el .env (o en los Secrets de GitHub):
    RESEND_API_KEY   -> cuenta gratis en resend.com > API Keys
    RESEND_FROM      -> remitente verificado en Resend.
                        Mientras no verifiques un dominio propio, usa
                        "onboarding@resend.dev" — pero ese remitente de
                        prueba SOLO deja enviar al correo con el que te
                        registraste en Resend (útil para probar, no para
                        producción con los 16 gestores reales).
"""
import os
import sys
from collections import defaultdict

# permite "from services import db" aunque el script esté en scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import requests

from services import db
from services import alertas as alertas_service

DIAS_ALERTA = int(os.environ.get("DIAS_ALERTA", "90"))
RESEND_API_KEY = os.environ["RESEND_API_KEY"]
RESEND_FROM = os.environ.get("RESEND_FROM", "onboarding@resend.dev")
TABLE_GESTORES = os.environ.get("TABLE_GESTORES", "gestores")

# Mientras el remitente sea el de prueba (onboarding@resend.dev), Resend
# SOLO deja enviar al correo con el que te registraste en Resend. Pon ese
# correo aquí (RESEND_OVERRIDE_TO en el .env) para probar el mecanismo
# completo sin tener que verificar un dominio todavía: todos los correos
# se mandan a esa dirección, pero cada uno dice para qué gestor era.
RESEND_OVERRIDE_TO = os.environ.get("RESEND_OVERRIDE_TO")


def correos_por_gestor() -> dict:
    """{nombre_gestor: correo}, tomado de la tabla gestores."""
    filas = db.get_table_items(TABLE_GESTORES, limit=200)
    return {f.get("nombre"): f.get("correo") for f in filas if f.get("correo")}


def construir_html(nombre_gestor: str, pendientes: list[dict]) -> str:
    filas = "".join(
        f"<tr><td>{p['pds']}</td><td>{p.get('establecimiento') or ''}</td>"
        f"<td>{p.get('ultima_visita') or 'Nunca visitado'}</td></tr>"
        for p in pendientes
    )
    return f"""
    <h2>PDS pendientes de visita — {nombre_gestor}</h2>
    <p>Tienes {len(pendientes)} PDS con más de {DIAS_ALERTA} días sin visita
    completa (o sin visitar todavía).</p>
    <table border="1" cellpadding="6" cellspacing="0">
      <tr><th>PDS</th><th>Establecimiento</th><th>Última visita</th></tr>
      {filas}
    </table>
    """


def enviar_correo(destinatario: str, asunto: str, html: str) -> dict:
    destino_real = destinatario
    if RESEND_OVERRIDE_TO:
        asunto = f"[prueba, para {destinatario}] {asunto}"
        destino_real = RESEND_OVERRIDE_TO

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={"from": RESEND_FROM, "to": [destino_real], "subject": asunto, "html": html},
        timeout=30,
    )
    if not resp.ok:
        # Resend explica el motivo exacto en el body (ej. remitente de
        # prueba, dominio no verificado, destinatario no permitido, etc.)
        print(f"Error de Resend ({resp.status_code}): {resp.text}")
    resp.raise_for_status()
    return resp.json()


def main():
    pendientes = alertas_service.pds_pendientes(DIAS_ALERTA)
    if not pendientes:
        print("No hay PDS pendientes — no se envía nada.")
        return

    por_gestor = defaultdict(list)
    for p in pendientes:
        gestor = p.get("gestor") or "Sin gestor asignado"
        por_gestor[gestor].append(p)

    correos = correos_por_gestor()
    enviados, sin_correo = 0, []

    for gestor, items in por_gestor.items():
        correo = correos.get(gestor)
        if not correo:
            sin_correo.append(gestor)
            continue
        enviar_correo(correo, f"Visitas ECB — {len(items)} PDS pendientes", construir_html(gestor, items))
        enviados += 1
        print(f"Enviado a {gestor} ({correo}): {len(items)} PDS pendientes")

    print(f"\nTotal correos enviados: {enviados}")
    if sin_correo:
        print(f"Gestores sin correo registrado (no se les pudo avisar): {', '.join(sin_correo)}")


if __name__ == "__main__":
    main()
