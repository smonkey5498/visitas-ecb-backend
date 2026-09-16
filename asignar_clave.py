# -*- coding: utf-8 -*-
"""
Asigna o cambia la clave de acceso de un gestor para el login del acta.

Solo Daya (o quien administre el backend) corre este script — el gestor
NO puede cambiar su propia clave desde el celular, así que si alguien
la olvida, aquí es donde se le pone una nueva.

Uso:
  python asignar_clave.py "Nombre exacto del gestor" "la-clave-nueva"

El nombre debe coincidir (sin importar mayúsculas ni espacios de más)
con el que aparece en la columna `nombre` de la tabla `gestores` en
Supabase. La clave debe tener al menos 6 caracteres.
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from services import db, auth

TABLE_GESTORES = "gestores"


def main():
    if len(sys.argv) != 3:
        print('Uso: python asignar_clave.py "Nombre del gestor" "clave"')
        sys.exit(1)

    nombre, clave = sys.argv[1], sys.argv[2]
    if len(clave) < 6:
        print("La clave debe tener al menos 6 caracteres.")
        sys.exit(1)

    gestor = auth.obtener_gestor_por_nombre(nombre)
    if not gestor:
        print(f"No encontré un gestor ACTIVO llamado '{nombre}' en la tabla '{TABLE_GESTORES}'.")
        print("Revisa que el nombre esté escrito igual que en Supabase y que su estado sea 'Activo'.")
        sys.exit(1)

    clave_hash = auth.hash_clave(clave)
    db.update_row(TABLE_GESTORES, {"nombre": gestor["nombre"]}, {"clave_hash": clave_hash})
    print(f"Listo: se asignó la clave a '{gestor['nombre']}'.")


if __name__ == "__main__":
    main()