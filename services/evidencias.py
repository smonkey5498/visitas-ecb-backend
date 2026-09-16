"""
Lógica de negocio de evidencias fotográficas (EVIDENCIAS_VISITA),
guardadas en Supabase Storage (bucket "evidencias").
"""
import os
import unicodedata
from datetime import datetime, timezone

from services import db

TABLE_EVIDENCIAS = os.environ.get("TABLE_EVIDENCIAS", "evidencias_visita")
TABLE_ACTAS = os.environ.get("TABLE_ACTAS", "actas_visita")
BUCKET_EVIDENCIAS = os.environ.get("BUCKET_EVIDENCIAS", "evidencias")


def _slug(texto: str) -> str:
    """Normaliza un texto para usarlo en la ruta del archivo (sin tildes ni espacios)."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    limpio = "".join(c if c.isalnum() else "_" for c in texto).strip("_")
    return limpio or "sin_dato"


def subir_evidencia(
    id_acta: int,
    pds: str,
    tipo: str,
    nombre_archivo: str,
    file_bytes: bytes,
    content_type: str,
    latitud: float | None = None,
    longitud: float | None = None,
) -> dict:
    """
    Sube la foto al bucket de Storage y guarda su registro en
    evidencias_visita, asociado al acta.
    Ruta en el bucket: <pds>/<id_acta>_<tipo>_<timestamp>.<ext>
    (así cada foto queda organizada por PDS y no se pisa con otras).
    """
    extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else "jpg"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ruta = f"{_slug(pds)}/{id_acta}_{_slug(tipo)}_{timestamp}.{extension}"

    url_publica = db.upload_photo(BUCKET_EVIDENCIAS, ruta, file_bytes, content_type)

    fila = db.create_row(TABLE_EVIDENCIAS, {
        "id_acta": id_acta,
        "tipo": tipo,
        "nombre_archivo": nombre_archivo,
        "ruta_archivo": ruta,
        "url_publica": url_publica,
        "latitud": latitud,
        "longitud": longitud,
    })
    return fila


def listar_evidencias(id_acta: int) -> list[dict]:
    """Evidencias guardadas de una acta (para revisarla o armar el informe)."""
    return db.get_table_items(TABLE_EVIDENCIAS, filters={"id_acta": id_acta}, limit=50)


def evidencias_por_pds(pds: str) -> list[dict]:
    """
    Todas las evidencias de todas las visitas de un PDS, de la más
    reciente a la más antigua — para la galería (Fase 17): revisar de
    un PDS puntual qué fotos se han subido a lo largo del tiempo.
    """
    actas = db.get_table_items(TABLE_ACTAS, filters={"pds": pds}, limit=200)

    resultado = []
    for acta in actas:
        id_acta = acta.get("id_acta")
        evidencias = db.get_table_items(TABLE_EVIDENCIAS, filters={"id_acta": id_acta}, limit=50)
        for ev in evidencias:
            ev["fecha_visita"] = acta.get("fecha_visita")
            ev["tipo_visita"] = acta.get("tipo_visita")
        resultado.extend(evidencias)

    resultado.sort(key=lambda ev: ev.get("fecha") or "", reverse=True)
    return resultado
