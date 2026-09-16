# -*- coding: utf-8 -*-
"""
Carga el catálogo de preguntas (PREGUNTAS_VISITA_consolidado.csv) directamente
a Supabase. El archivo está separado por ";" (así lo exporta Excel en español),
e incluye una columna opcional "DependeDe" para preguntas que solo se muestran
según la respuesta de otra pregunta (formato "ID_Pregunta=Valor1|Valor2").

Este script hace un REEMPLAZO COMPLETO del catálogo (borra todo lo que había
en la tabla y carga de nuevo desde el CSV), no un upsert: así, si cambiaste
IDs o resumiste preguntas, no quedan filas viejas "huérfanas" con IDs que ya
no existen en el archivo. Esto no toca las respuestas ya guardadas de actas
anteriores (tabla aparte); solo afecta el catálogo de preguntas.

Uso:
  python migrar_preguntas_csv.py
"""
import csv
import os
from dotenv import load_dotenv

load_dotenv()

from services import db

RUTA_CSV = os.environ.get("RUTA_CSV_PREGUNTAS", "PREGUNTAS_VISITA_consolidado.csv")
TABLE_PREGUNTAS = os.environ.get("TABLE_PREGUNTAS", "preguntas_visita")

# encabezado del CSV -> columna en Supabase
MAPA = {
    "ID_Pregunta": "id_pregunta",
    "Seccion": "seccion",
    "Pregunta": "pregunta",
    "TipoRespuesta": "tiporespuesta",
    "Obligatoria": "obligatoria",
    "Activo": "activo",
    "Orden": "orden",
    "Opciones": "opciones",
    "AplicaVisita": "aplica_visita",
    "DependeDe": "depende_de",
}


def main():
    with open(RUTA_CSV, encoding="utf-8") as f:
        lector = csv.DictReader(f, delimiter=";")
        filas = []
        for r in lector:
            if not r.get("ID_Pregunta"):
                continue
            fila = {MAPA[k]: v for k, v in r.items() if k in MAPA}
            if fila.get("orden"):
                fila["orden"] = int(fila["orden"])
            # depende_de vacío -> None (para no guardar strings vacíos)
            if not fila.get("depende_de"):
                fila["depende_de"] = None
            filas.append(fila)

    print(f"Leídas {len(filas)} preguntas de {RUTA_CSV}")

    db._client.table(TABLE_PREGUNTAS).delete().neq("id_pregunta", "___nunca___").execute()
    db._client.table(TABLE_PREGUNTAS).upsert(filas).execute()
    print(f"Cargadas {len(filas)} preguntas en la tabla '{TABLE_PREGUNTAS}' (reemplazo completo).")


if __name__ == "__main__":
    main()