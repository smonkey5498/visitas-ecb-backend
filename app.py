"""
API de digitalización de visitas ECB.
Misma forma que tu app.py original — el cambio de SharePoint a Supabase
ocurrió por debajo, en services/db.py y services/pds.py.
"""
from dotenv import load_dotenv
load_dotenv()

from typing import Optional

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from services import pds as pds_service
from services import preguntas as preguntas_service
from services import visitas as visitas_service
from services import evidencias as evidencias_service
from services import alertas as alertas_service
from services import gestores as gestores_service


class ActualizacionPDS(BaseModel):
    gestor: str
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


app = FastAPI(title="Visitas ECB")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/galeria")
def galeria(request: Request):
    return templates.TemplateResponse("galeria.html", {"request": request})


@app.get("/acta")
def acta(request: Request):
    return templates.TemplateResponse("acta.html", {"request": request})


@app.get("/gestores")
def listar_gestores():
    return gestores_service.listar_gestores()


@app.get("/pds/{codigo_pds}")
def obtener_pds(codigo_pds: str):
    resultado = pds_service.obtener_pds(codigo_pds)
    if resultado is None:
        raise HTTPException(status_code=404, detail=f"No existe el PDS '{codigo_pds}'")
    return resultado


@app.get("/gestores/{nombre_gestor}/pds")
def listar_pds_por_gestor(nombre_gestor: str):
    return pds_service.listar_pds_por_gestor(nombre_gestor)


@app.put("/pds/{codigo_pds}")
def actualizar_pds(codigo_pds: str, body: ActualizacionPDS):
    resultado = pds_service.actualizar_pds(codigo_pds, body.model_dump())
    if resultado is None:
        raise HTTPException(status_code=404, detail=f"No existe el PDS '{codigo_pds}'")
    return resultado


@app.get("/preguntas")
def listar_preguntas(tipo_visita: str):
    return preguntas_service.listar_preguntas(tipo_visita)


@app.post("/visitas/iniciar")
def iniciar_visita(body: IniciarVisita):
    return visitas_service.iniciar_visita(
        body.pds, body.gestor, body.tipo_visita,
        body.latitud, body.longitud, body.precision_gps,
    )


@app.post("/respuestas")
def guardar_respuestas(body: GuardarRespuestas):
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
def cerrar_visita(id_acta: int, body: CerrarVisita):
    return visitas_service.cerrar_visita(id_acta, body.observaciones)


@app.get("/alertas/pds-pendientes")
def alertas_pds_pendientes(dias: int = 90):
    return alertas_service.pds_pendientes(dias)
