"""
API de digitalización de visitas ECB.
Misma forma que tu app.py original — el cambio de SharePoint a Supabase
ocurrió por debajo, en services/db.py y services/pds.py.
"""
from dotenv import load_dotenv
load_dotenv()

from typing import Optional

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Header, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from services import pds as pds_service
from services import preguntas as preguntas_service
from services import visitas as visitas_service
from services import evidencias as evidencias_service
from services import alertas as alertas_service
from services import gestores as gestores_service
from services import auth as auth_service
from services import oficinas as oficinas_service


class ActualizacionPDS(BaseModel):
    motivo: Optional[str] = None
    identificacion_titular: Optional[str] = None
    nombre_titular: Optional[str] = None
    nombre_establecimiento: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    telefono2: Optional[str] = None
    regimen: Optional[str] = None
    facturador_electronico: Optional[str] = None
    residente: Optional[str] = None
    correo: Optional[str] = None
    ciudad: Optional[str] = None
    zona: Optional[str] = None


class IniciarVisita(BaseModel):
    pds: str
    gestor: str
    tipo_visita: str  # Prospección | Seguimiento | Oficina
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    precision_gps: Optional[float] = None  # metros, del GPS del celular (accuracy)


class Respuesta(BaseModel):
    id_pregunta: str
    respuesta: Optional[str] = None
    observacion: Optional[str] = None


class GuardarRespuestas(BaseModel):
    id_acta: int
    respuestas: list[Respuesta]


class CerrarVisita(BaseModel):
    observaciones: Optional[str] = None


class LoginBody(BaseModel):
    usuario: str
    clave: str


app = FastAPI(title="Visitas ECB")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def gestor_autenticado(authorization: Optional[str] = Header(default=None)) -> str:
    """
    Dependencia de FastAPI: exige "Authorization: Bearer <token>" válido
    y devuelve el nombre del gestor dueño de la sesión (nunca confiamos
    en un "gestor" que venga suelto en el body de la petición).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Debes iniciar sesión.")
    token = authorization.split(" ", 1)[1].strip()
    nombre = auth_service.verificar_token(token)
    if not nombre:
        raise HTTPException(status_code=401, detail="Tu sesión venció, inicia sesión de nuevo.")
    return nombre


@app.get("/")
def home():
    # La página de inicio real de los gestores es el acta; index.html es una
    # página de prueba vieja de las primeras fases del proyecto.
    return RedirectResponse(url="/acta")


@app.get("/galeria")
def galeria(request: Request):
    return templates.TemplateResponse("galeria.html", {"request": request})


@app.get("/acta")
def acta(request: Request):
    return templates.TemplateResponse("acta.html", {"request": request})


@app.post("/login")
def login(body: LoginBody):
    gestor = auth_service.autenticar(body.usuario, body.clave)
    if not gestor:
        raise HTTPException(status_code=401, detail="Usuario o clave incorrectos.")
    token = auth_service.crear_token(gestor["nombre"])
    return {"token": token, "gestor": gestor["nombre"]}


@app.get("/gestores")
def listar_gestores():
    return gestores_service.listar_gestores()


@app.get("/oficinas")
def listar_oficinas():
    return oficinas_service.listar_oficinas()


@app.get("/pds/{codigo_pds}")
def obtener_pds(codigo_pds: str):
    resultado = pds_service.obtener_pds(codigo_pds)
    if resultado is None:
        raise HTTPException(status_code=404, detail=f"No existe el PDS '{codigo_pds}'")
    return resultado


@app.get("/gestores/{nombre_gestor}/pds")
def listar_pds_por_gestor(nombre_gestor: str):
    return pds_service.listar_pds_por_gestor(nombre_gestor)


@app.get("/pds/{codigo_pds}/ultimas-respuestas")
def ultimas_respuestas_pds(codigo_pds: str, gestor: str = Depends(gestor_autenticado)):
    return visitas_service.ultimas_respuestas(codigo_pds)


@app.put("/pds/{codigo_pds}")
def actualizar_pds(
    codigo_pds: str,
    body: ActualizacionPDS,
    gestor: str = Depends(gestor_autenticado),
):
    datos = body.model_dump()
    datos["gestor"] = gestor  # el gestor autenticado, nunca uno suelto en el body
    resultado = pds_service.actualizar_pds(codigo_pds, datos)
    if resultado is None:
        raise HTTPException(status_code=404, detail=f"No existe el PDS '{codigo_pds}'")
    return resultado


@app.get("/preguntas")
def listar_preguntas(tipo_visita: str):
    return preguntas_service.listar_preguntas(tipo_visita)


@app.post("/visitas/iniciar")
def iniciar_visita(body: IniciarVisita, gestor: str = Depends(gestor_autenticado)):
    return visitas_service.iniciar_visita(
        body.pds, gestor, body.tipo_visita,
        body.latitud, body.longitud, body.precision_gps,
    )


@app.post("/respuestas")
def guardar_respuestas(body: GuardarRespuestas, gestor: str = Depends(gestor_autenticado)):
    return visitas_service.guardar_respuestas(
        body.id_acta, [r.model_dump() for r in body.respuestas]
    )


@app.post("/evidencias")
async def subir_evidencia(
    id_acta: int = Form(...),
    pds: str = Form(...),
    tipo: str = Form(...),
    latitud: Optional[float] = Form(None),
    longitud: Optional[float] = Form(None),
    archivo: UploadFile = File(...),
    gestor: str = Depends(gestor_autenticado),
):
    contenido = await archivo.read()
    return evidencias_service.subir_evidencia(
        id_acta, pds, tipo, archivo.filename, contenido,
        archivo.content_type or "image/jpeg", latitud, longitud,
    )


@app.get("/visitas/{id_acta}/evidencias")
def listar_evidencias(id_acta: int):
    return evidencias_service.listar_evidencias(id_acta)


@app.get("/pds/{codigo_pds}/evidencias")
def evidencias_por_pds(codigo_pds: str):
    return evidencias_service.evidencias_por_pds(codigo_pds)


@app.post("/visitas/{id_acta}/cerrar")
def cerrar_visita(id_acta: int, body: CerrarVisita, gestor: str = Depends(gestor_autenticado)):
    return visitas_service.cerrar_visita(id_acta, body.observaciones)


@app.get("/alertas/pds-pendientes")
def alertas_pds_pendientes(dias: int = 90):
    return alertas_service.pds_pendientes(dias)
