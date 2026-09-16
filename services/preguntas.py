"""
Lógica de negocio del catálogo de preguntas del acta (PREGUNTAS_VISITA).
"""
import os
from services import db

TABLE_PREGUNTAS = os.environ.get("TABLE_PREGUNTAS", "preguntas_visita")


def listar_preguntas(tipo_visita: str) -> list[dict]:
    """
    Devuelve las preguntas activas que aplican a este tipo de visita
    (Prospección | Seguimiento | Oficina), ordenadas por sección y orden.

    `aplica_visita` guarda uno o varios tipos separados por coma
    (ej. "Prospección, Seguimiento"), así que se filtra por "contiene"
    el tipo pedido, no por igualdad exacta. Son ~104 preguntas en total,
    así que se traen todas las activas y se filtran en Python.
    """
    todas = db.get_table_items(TABLE_PREGUNTAS, filters={"activo": "Si"}, limit=500)

    tipo = tipo_visita.strip().lower()
    filtradas = [
        p for p in todas
        if tipo in (p.get("aplica_visita") or "").lower()
    ]

    filtradas.sort(key=lambda p: (p.get("seccion") or "", p.get("orden") or 0))
    return filtradas
