"""
Cliente de Supabase (Postgres + Storage) — reemplaza a services/sharepoint.py.

Por qué Supabase en lugar de SharePoint/Graph:
- No depende de registrar una aplicación en Azure AD ni de permisos de TI:
  te creas una cuenta gratuita con tu correo y ya tienes una base de datos
  Postgres real + almacenamiento de archivos (para las fotos), todo en un
  mismo lugar.
- Los gestores nunca tocan Supabase directamente: siguen hablando solo con
  tu API (FastAPI), exactamente igual que antes. Lo único que cambió es
  dónde vive el dato — el resto del backend (app.py, services/pds.py) casi
  no cambia de forma.

Requiere en el .env:
  SUPABASE_URL          -> Project Settings > API > Project URL
  SUPABASE_SERVICE_KEY  -> Project Settings > API > service_role key
                           (NO la "anon" key: el backend necesita leer y
                           escribir sin las restricciones de Row Level
                           Security que aplican a un usuario final. La
                           service_role key nunca debe usarse en el
                           navegador, solo aquí en el servidor.)
"""
import os
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class DBError(Exception):
    """Error de comunicación con Supabase."""


def get_table_items(table_name: str, filters: dict | None = None, limit: int = 50) -> list[dict]:
    """
    Equivalente a sharepoint.get_list_items: devuelve filas de una tabla
    como lista de diccionarios {columna: valor}.

    filters: {"columna": "valor"} -> igualdad exacta (se pueden combinar varias)
    """
    try:
        query = _client.table(table_name).select("*")
        if filters:
            for col, val in filters.items():
                query = query.eq(col, val)
        resp = query.limit(limit).execute()
        return resp.data
    except Exception as e:
        raise DBError(f"Error consultando la tabla '{table_name}': {e}")


def create_row(table_name: str, fields: dict) -> dict:
    """Crea un nuevo registro (fila) en una tabla. Devuelve la fila creada."""
    try:
        resp = _client.table(table_name).insert(fields).execute()
        return resp.data[0] if resp.data else {}
    except Exception as e:
        raise DBError(f"Error creando fila en '{table_name}': {e}")


def create_rows(table_name: str, rows: list[dict]) -> list[dict]:
    """Crea varios registros de una vez (para cargas masivas, ej. migración)."""
    try:
        resp = _client.table(table_name).insert(rows).execute()
        return resp.data
    except Exception as e:
        raise DBError(f"Error creando filas en '{table_name}': {e}")


def update_row(table_name: str, match: dict, fields: dict) -> dict:
    """Actualiza las filas que cumplan `match` con los valores de `fields`."""
    try:
        query = _client.table(table_name).update(fields)
        for col, val in match.items():
            query = query.eq(col, val)
        resp = query.execute()
        return resp.data[0] if resp.data else {}
    except Exception as e:
        raise DBError(f"Error actualizando '{table_name}': {e}")


def upload_photo(bucket: str, path: str, file_bytes: bytes, content_type: str = "image/jpeg") -> str:
    """
    Sube una foto al bucket de Supabase Storage y devuelve su URL pública.
    path ej: "PDS_100001/2026-09-15_fachada.jpg"

    Antes de usar esto, crea el bucket una vez en el panel de Supabase:
    Storage -> New bucket -> nombre "evidencias" -> marca "Public bucket".
    """
    try:
        _client.storage.from_(bucket).upload(
            path, file_bytes, {"content-type": content_type, "upsert": "true"}
        )
        return _client.storage.from_(bucket).get_public_url(path)
    except Exception as e:
        raise DBError(f"Error subiendo foto a '{bucket}/{path}': {e}")
