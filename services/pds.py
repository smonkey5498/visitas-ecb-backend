"""
Lógica de negocio relacionada con PDS (puntos de servicio).
"""
import os
from datetime import datetime, timezone
from services import db

TABLE_PDS = os.environ.get("TABLE_PDS", "pds")
TABLE_CAMBIOS = os.environ.get("TABLE_CAMBIOS", "cambios_pds")

# Campos que un gestor puede corregir desde el acta. "pds" (la llave),
# "gestor" y "estado" quedan fuera a propósito — no se tocan desde aquí.
CAMPOS_EDITABLES = [
    "identificacion_titular",
    "nombre_titular",
    "nombre_establecimiento",
    "direccion",
    "telefono",
    "telefono2",
    "regimen",
    "facturador_electronico",
    "residente",
    "correo",
    "ciudad",
    "zona",
]


def obtener_pds(codigo_pds: str) -> dict | None:
    """
    Busca un PDS por su código (llave principal) y devuelve
    el formato reducido que consume la app móvil.
    Devuelve None si no existe.
    """
    items = db.get_table_items(TABLE_PDS, filters={"pds": codigo_pds}, limit=1)

    if not items:
        return None

    fila = items[0]
    return {
        "pds": fila.get("pds"),
        "titular": fila.get("nombre_titular"),
        "establecimiento": fila.get("nombre_establecimiento"),
        "direccion": fila.get("direccion"),
        "telefono": fila.get("telefono"),
        "correo": fila.get("correo"),
        "gestor": fila.get("gestor"),
        # útil para validar la distancia GPS en la visita (Fase 13)
        "latitud_referencia": fila.get("latitud_referencia"),
        "longitud_referencia": fila.get("longitud_referencia"),
    }


def listar_pds_por_gestor(nombre_gestor: str) -> list[dict]:
    """
    Devuelve los PDS asignados a un gestor (para la pantalla "Mis PDS").
    La columna `gestor` de la tabla `pds` guarda el NOMBRE del gestor
    (igual que en el Excel original), no el `id_gestor` de la tabla
    `gestores` — por eso se filtra por nombre tal cual.
    """
    items = db.get_table_items(TABLE_PDS, filters={"gestor": nombre_gestor}, limit=200)

    return [
        {
            "pds": fila.get("pds"),
            "establecimiento": fila.get("nombre_establecimiento"),
            "direccion": fila.get("direccion"),
        }
        for fila in items
    ]


def actualizar_pds(codigo_pds: str, datos: dict) -> dict | None:
    """
    Compara los campos que envía el gestor contra lo que ya está guardado.
    Por cada campo distinto: registra el cambio en `cambios_pds` (auditoría)
    y actualiza el maestro en `pds`. Los campos que no vienen en `datos`
    (None) o que no cambiaron no generan ni auditoría ni actualización.

    `datos` trae además "gestor" (obligatorio: quién hizo el cambio) y
    "motivo" (opcional).

    Devuelve None si el PDS no existe.
    """
    items = db.get_table_items(TABLE_PDS, filters={"pds": codigo_pds}, limit=1)
    if not items:
        return None
    actual = items[0]

    gestor = datos.get("gestor")
    motivo = datos.get("motivo")

    nuevos_valores = {}
    auditoria = []
    for campo in CAMPOS_EDITABLES:
        nuevo = datos.get(campo)
        if nuevo is None:
            continue  # el gestor no envió este campo -> no se toca
        anterior = (actual.get(campo) or "").strip()
        nuevo_limpio = str(nuevo).strip()
        if nuevo_limpio != anterior:
            nuevos_valores[campo] = nuevo_limpio
            auditoria.append({
                "pds": codigo_pds,
                "campo_modificado": campo,
                "valor_anterior": anterior,
                "valor_nuevo": nuevo_limpio,
                "gestor": gestor,
                "motivo": motivo,
                "estado_sincronizacion": "Aplicado",
            })

    if auditoria:
        db.create_rows(TABLE_CAMBIOS, auditoria)
        nuevos_valores["fecha_actualizacion"] = datetime.now(timezone.utc).isoformat()
        db.update_row(TABLE_PDS, match={"pds": codigo_pds}, fields=nuevos_valores)

    return {
        "pds": codigo_pds,
        "cambios_aplicados": len(auditoria),
        "campos_modificados": [a["campo_modificado"] for a in auditoria],
    }
