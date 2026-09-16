# -*- coding: utf-8 -*-
"""
Autenticación de gestores para el acta.

Cómo funciona (decisión de Daya: ella asigna la clave, el gestor NO
puede cambiarla desde el celular):
- Daya le asigna/actualiza la clave a cada gestor corriendo
  `python asignar_clave.py "Nombre del gestor" "la-clave"` — eso guarda
  solo un hash (bcrypt) en la columna `clave_hash` de la tabla
  `gestores`, nunca la clave en texto plano.
- El gestor abre `/acta`, escribe su nombre (tal como está en la tabla
  `gestores`) y esa clave -> `POST /login` valida y devuelve un token.
- Ese token se manda en cada llamada protegida como
  "Authorization: Bearer <token>". Si el token es inválido o ya venció
  (SESION_DIAS, por defecto 30 días), la llamada responde 401 y el
  celular vuelve a pedir el login.

Requiere en el .env: SECRET_KEY (una cadena larga y aleatoria, nunca la
misma que uses en otro proyecto) y opcionalmente SESION_DIAS.
"""
import os
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from services import db

TABLE_GESTORES = os.environ.get("TABLE_GESTORES", "gestores")
SECRET_KEY = os.environ["SECRET_KEY"]
SESION_DIAS = int(os.environ.get("SESION_DIAS", "30"))

_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="sesion-gestor")


def hash_clave(clave: str) -> str:
    """Nunca guardamos la clave, solo este hash (bcrypt, con su propia sal)."""
    return bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verificar_clave(clave: str, clave_hash: str) -> bool:
    try:
        return bcrypt.checkpw(clave.encode("utf-8"), clave_hash.encode("utf-8"))
    except (ValueError, AttributeError, TypeError):
        return False


def obtener_gestor_por_nombre(nombre: str) -> dict | None:
    """
    Busca un gestor activo por nombre, sin distinguir mayúsculas/espacios
    de más (para que un error de tipeo menor al hacer login no bloquee
    al gestor).
    """
    filas = db.get_table_items(TABLE_GESTORES, filters={"estado": "Activo"}, limit=200)
    nombre_norm = (nombre or "").strip().lower()
    for f in filas:
        if (f.get("nombre") or "").strip().lower() == nombre_norm:
            return f
    return None


def autenticar(usuario: str, clave: str) -> dict | None:
    """Devuelve la fila del gestor si el usuario/clave son correctos, si no None."""
    gestor = obtener_gestor_por_nombre(usuario)
    if not gestor or not gestor.get("clave_hash"):
        return None
    if not _verificar_clave(clave or "", gestor["clave_hash"]):
        return None
    return gestor


def crear_token(nombre_gestor: str) -> str:
    return _serializer.dumps({"gestor": nombre_gestor})


def verificar_token(token: str) -> str | None:
    """Devuelve el nombre del gestor si el token es válido y no ha vencido."""
    try:
        datos = _serializer.loads(token, max_age=SESION_DIAS * 86400)
        return datos.get("gestor")
    except (BadSignature, SignatureExpired):
        return None
