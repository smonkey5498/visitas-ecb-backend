# -*- coding: utf-8 -*-
"""
Migra tus datos reales desde "Plantilla_Digitalizacion_visitas_ECB.xlsx"
hacia Supabase: hojas GESTORES, PDS y PREGUNTAS_VISITA.

Cómo usarlo:
  1. Asegúrate de haber corrido schema.sql en el SQL Editor de Supabase antes.
  2. Copia tu archivo .xlsx a esta misma carpeta (o ajusta RUTA_EXCEL abajo).
  3. Completa tu .env (ver .env.example).
  4. pip install -r requirements.txt
  5. python migrar_datos.py

Es seguro volver a correrlo: si una fila con el mismo PDS/ID_Gestor ya
existe, este script la actualiza en vez de duplicarla (upsert).

Si tus encabezados de columna en el Excel no son EXACTAMENTE los mismos
que se ven en MAPA_PDS / MAPA_GESTORES abajo, el script te va a avisar
cuáles no reconoció, sin detenerse ni dañar nada.
"""
import os
import sys
import unicodedata
from dotenv import load_dotenv

load_dotenv()

import openpyxl
from services import db

RUTA_EXCEL = os.environ.get(
    "RUTA_EXCEL_PORTAFOLIO", "Plantilla_Digitalizacion_visitas_ECB - copia.xlsx"
)

TABLE_GESTORES = os.environ.get("TABLE_GESTORES", "gestores")
TABLE_PDS = os.environ.get("TABLE_PDS", "pds")
TABLE_PREGUNTAS = os.environ.get("TABLE_PREGUNTAS", "preguntas_visita")

LOTE = 300  # filas por tanda de inserción


def _norm(s: str) -> str:
    """Normaliza un encabezado para compararlo sin importar tildes/mayúsculas/espacios."""
    s = str(s or "").strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.lower().replace(" ", "").replace("_", "")


# columna_en_supabase -> lista de encabezados posibles en el Excel (se prueban en orden)
MAPA_PDS = {
    "pds": ["PDS"],
    "identificacion_titular": ["IdentificacionTitular"],
    "nombre_titular": ["NombreTitular"],
    "nombre_establecimiento": ["NombreEstablecimiento"],
    "direccion": ["Direccion", "Dirección"],
    "telefono": ["Telefono", "Teléfono"],
    "telefono2": ["Telefono2", "Teléfono2"],
    "regimen": ["RÉGIMEN", "REGIMEN", "Régimen"],
    "facturador_electronico": ["FACTURADOR ELECTRÓNICO", "FACTURADOR ELECTRONICO"],
    "residente": ["RESIDENTE"],
    "correo": ["Correo"],
    "ciudad": ["Ciudad"],
    "zona": ["Zona"],
    "gestor": ["Gestor"],
    "estado": ["Estado"],
}

MAPA_GESTORES = {
    "id_gestor": ["ID_Gestor"],
    "nombre": ["Nombre"],
    "correo": ["Correo"],
    "zona": ["Zona"],
    "estado": ["Estado"],
}

MAPA_PREGUNTAS = {
    "id_pregunta": ["ID_Pregunta"],
    "seccion": ["Seccion", "Sección"],
    "pregunta": ["Pregunta"],
    "tiporespuesta": ["TipoRespuesta"],
    "obligatoria": ["Obligatoria"],
    "activo": ["Activo"],
    "orden": ["Orden"],
    "opciones": ["Opciones"],
    "aplica_visita": ["AplicaVisita"],
}


def leer_hoja(ws, mapa: dict) -> list[dict]:
    encabezados = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    encabezados_norm = [_norm(h) for h in encabezados]

    columnas = {}  # col_supabase -> índice de columna en el excel
    no_encontradas = []
    for col_supabase, posibles in mapa.items():
        idx = None
        for posible in posibles:
            if _norm(posible) in encabezados_norm:
                idx = encabezados_norm.index(_norm(posible))
                break
        if idx is None:
            no_encontradas.append(col_supabase)
        else:
            columnas[col_supabase] = idx

    if no_encontradas:
        print(f"  AVISO: no encontré estas columnas en la hoja (se dejan vacías): {no_encontradas}")
        print(f"  Encabezados reales de la hoja: {encabezados}")

    filas = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        fila = {}
        for col_supabase, idx in columnas.items():
            val = row[idx] if idx < len(row) else None
            fila[col_supabase] = "" if val is None else str(val).strip()
        # nunca migrar una fila sin llave principal
        llave = "pds" if "pds" in mapa else ("id_gestor" if "id_gestor" in mapa else "id_pregunta")
        if fila.get(llave):
            filas.append(fila)
    return filas


def cargar(table_name: str, filas: list[dict], etiqueta: str):
    if not filas:
        print(f"  {etiqueta}: 0 filas, nada que cargar.")
        return
    total = 0
    for i in range(0, len(filas), LOTE):
        lote = filas[i : i + LOTE]
        try:
            db._client.table(table_name).upsert(lote).execute()
            total += len(lote)
            print(f"  {etiqueta}: {total}/{len(filas)} filas cargadas...")
        except Exception as e:
            print(f"  ERROR cargando lote {i}-{i+len(lote)} en '{table_name}': {e}")
            sys.exit(1)
    print(f"  {etiqueta}: listo, {total} filas en total.")


def main():
    print(f"Abriendo {RUTA_EXCEL} ...")
    wb = openpyxl.load_workbook(RUTA_EXCEL, data_only=True)
    print("Hojas encontradas:", wb.sheetnames)

    if "GESTORES" in wb.sheetnames:
        print("\n--- GESTORES ---")
        filas = leer_hoja(wb["GESTORES"], MAPA_GESTORES)
        cargar(TABLE_GESTORES, filas, "gestores")
    else:
        print("\n(No encontré una hoja 'GESTORES', se omite)")

    if "PDS" in wb.sheetnames:
        print("\n--- PDS ---")
        filas = leer_hoja(wb["PDS"], MAPA_PDS)
        cargar(TABLE_PDS, filas, "pds")
    else:
        print("\n(No encontré una hoja 'PDS', se omite)")

    if "PREGUNTAS_VISITA" in wb.sheetnames:
        print("\n--- PREGUNTAS_VISITA ---")
        filas = leer_hoja(wb["PREGUNTAS_VISITA"], MAPA_PREGUNTAS)
        cargar(TABLE_PREGUNTAS, filas, "preguntas_visita")
    else:
        print("\n(No encontré una hoja 'PREGUNTAS_VISITA' en este Excel.")
        print(" Si ya tienes PREGUNTAS_VISITA_consolidado.csv, cárgalo aparte")
        print(" con el mismo patrón, o pide ayuda para el script equivalente.)")

    print("\nMigración terminada. Revisa las tablas en Supabase -> Table Editor.")


if __name__ == "__main__":
    main()
