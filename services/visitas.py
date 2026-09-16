"""
Lógica de negocio del acta de visita: encabezado (ACTAS_VISITA) y
respuestas (RESPUESTAS_VISITA).
"""
import os
from datetime import datetime, timezone
from math import radians, sin, cos, sqrt, atan2

from services import db
from services import pds as pds_service

TABLE_ACTAS = os.environ.get("TABLE_ACTAS", "actas_visita")
TABLE_RESPUESTAS = os.environ.get("TABLE_RESPUESTAS", "respuestas_visita")

RADIO_TIERRA_METROS = 6371000


def calcular_distancia_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Distancia en línea recta entre dos coordenadas GPS (fórmula de
    Haversine). Se usa para comparar el punto donde el gestor abrió
    el acta contra la ubicación de referencia guardada del PDS.
    """
    f1, f2 = radians(lat1), radians(lat2)
    df = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(df / 2) ** 2 + cos(f1) * cos(f2) * sin(dl / 2) ** 2
    return RADIO_TIERRA_METROS * 2 * atan2(sqrt(a), sqrt(1 - a))


def iniciar_visita(
    pds: str,
    gestor: str,
    tipo_visita: str,
    latitud: float | None = None,
    longitud: float | None = None,
    precision_gps: float | None = None,
) -> dict:
    """
    Crea el encabezado de una visita (acta) y devuelve su id_acta.
    Si el celular envía GPS (latitud/longitud), se compara contra la
    latitud_referencia/longitud_referencia guardada del PDS y se
    guarda la distancia en metros (distancia_pds) — así queda registro
    de si la visita se abrió realmente en el punto o no.
    Las fotos (Fase 14) y el cierre (Fase 15) se agregan después,
    sobre esta misma acta — por eso queda "En curso".
    """
    distancia_pds = None
    if latitud is not None and longitud is not None:
        info_pds = pds_service.obtener_pds(pds)
        if info_pds is not None:
            lat_ref = info_pds.get("latitud_referencia")
            lon_ref = info_pds.get("longitud_referencia")
            if lat_ref is not None and lon_ref is not None:
                distancia_pds = calcular_distancia_metros(latitud, longitud, lat_ref, lon_ref)

    fila = db.create_row(TABLE_ACTAS, {
        "pds": pds,
        "gestor": gestor,
        "tipo_visita": tipo_visita,
        "estado_visita": "En curso",
        "hora_inicio": datetime.now(timezone.utc).time().isoformat(),
        "latitud": latitud,
        "longitud": longitud,
        "precision_gps": precision_gps,
        "distancia_pds": distancia_pds,
    })
    return {"id_acta": fila.get("id_acta"), "distancia_pds": distancia_pds}


def cerrar_visita(id_acta: int, observaciones: str | None = None) -> dict:
    """
    Cierra el acta: registra la hora_fin y pasa estado_visita de
    "En curso" a "Completa". Se llama al final, después de guardar
    las respuestas y las evidencias de esa acta.
    """
    campos = {
        "estado_visita": "Completa",
        "hora_fin": datetime.now(timezone.utc).time().isoformat(),
    }
    if observaciones is not None:
        campos["observaciones"] = observaciones
    return db.update_row(TABLE_ACTAS, match={"id_acta": id_acta}, fields=campos)


def guardar_respuestas(id_acta: int, respuestas: list[dict]) -> dict:
    """
    Guarda las respuestas de una acta. `respuestas` es una lista de
    {id_pregunta, respuesta, observacion}.
    """
    filas = [
        {
            "id_acta": id_acta,
            "id_pregunta": r.get("id_pregunta"),
            "respuesta": r.get("respuesta"),
            "observacion": r.get("observacion"),
        }
        for r in respuestas
    ]
    if filas:
        db.create_rows(TABLE_RESPUESTAS, filas)
    return {"id_acta": id_acta, "respuestas_guardadas": len(filas)}
