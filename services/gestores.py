"""
Lógica de negocio del catálogo de gestores (GESTORES) — usado para
poblar el selector de "quién está diligenciando" en el acta.
"""
import os
from services import db

TABLE_GESTORES = os.environ.get("TABLE_GESTORES", "gestores")


def listar_gestores() -> list[dict]:
    """Gestores activos, para el selector del acta."""
    filas = db.get_table_items(TABLE_GESTORES, filters={"estado": "Activo"}, limit=200)
    return [{"nombre": f.get("nombre"), "zona": f.get("zona")} for f in filas]
