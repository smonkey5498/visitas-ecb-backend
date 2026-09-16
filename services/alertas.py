"""
Lógica de negocio de alertas de seguimiento: qué PDS llevan más de
N días (90 por defecto) sin una visita completa, o que nunca han
sido visitados.
"""
import os
from datetime import date, timedelta

from services import db

TABLE_PDS = os.environ.get("TABLE_PDS", "pds")
TABLE_ACTAS = os.environ.get("TABLE_ACTAS", "actas_visita")


def pds_pendientes(dias: int = 90) -> list[dict]:
    """
    Devuelve los PDS activos cuya última visita "Completa" tiene más
    de `dias` días (o que nunca han tenido una visita completa),
    ordenados del más atrasado al menos atrasado.
    """
    limite = (date.today() - timedelta(days=dias)).isoformat()

    todos_pds = db.get_table_items(TABLE_PDS, filters={"estado": "Activo"}, limit=2000)
    actas_completas = db.get_table_items(TABLE_ACTAS, filters={"estado_visita": "Completa"}, limit=5000)

    # última fecha de visita completa por pds
    ultima_visita: dict[str, str] = {}
    for acta in actas_completas:
        codigo = acta.get("pds")
        fecha = acta.get("fecha_visita")
        if not codigo or not fecha:
            continue
        if codigo not in ultima_visita or fecha > ultima_visita[codigo]:
            ultima_visita[codigo] = fecha

    pendientes = []
    for p in todos_pds:
        codigo = p.get("pds")
        fecha_ultima = ultima_visita.get(codigo)
        if fecha_ultima is None or fecha_ultima < limite:
            pendientes.append({
                "pds": codigo,
                "establecimiento": p.get("nombre_establecimiento"),
                "gestor": p.get("gestor"),
                "ultima_visita": fecha_ultima,  # None = nunca visitado
            })

    # los que nunca se han visitado (None) primero, luego los más antiguos
    pendientes.sort(key=lambda x: x["ultima_visita"] or "")
    return pendientes
