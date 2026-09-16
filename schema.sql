-- ============================================================================
-- Esquema de base de datos — Digitalización de visitas ECB
-- Reemplaza a las 7 listas de SharePoint por 7 tablas de Postgres (Supabase).
--
-- Cómo usarlo:
--   1. Entra a tu proyecto en supabase.com -> panel izquierdo -> "SQL Editor"
--   2. Pega TODO este archivo -> botón "Run"
--   3. Confirma en "Table Editor" que aparecieron las 7 tablas
--
-- Convención: nombres de tabla y columna en minúsculas y snake_case
-- (es el estándar de Postgres; evita tener que escribir comillas siempre).
-- El mapeo con los nombres originales del Excel/Word está en migrar_datos.py.
--
-- Nota sobre llaves foráneas: solo se usan donde el dato se genera dentro
-- del propio sistema (id_acta, que crea el backend). Los campos "pds" y
-- "gestor" que vienen de tus archivos NO tienen llave foránea a propósito:
-- así una carga con datos inconsistentes, o una visita de Prospección cuyo
-- PDS todavía no existe en el portafolio, no rompe la inserción. La
-- consistencia de esos campos se valida en el backend (Fase 11+), no en la
-- base de datos.
-- ============================================================================

-- 1) GESTORES ---------------------------------------------------------------
create table if not exists gestores (
    id_gestor           text primary key,
    nombre              text not null,
    correo              text,
    zona                text,
    estado              text default 'Activo'
);

-- 2) PDS (portafolio de corresponsales) --------------------------------------
-- La llave es el código PDS, nunca la cédula ni el nombre del establecimiento
-- (una misma cédula puede tener varios PDS).
create table if not exists pds (
    pds                     text primary key,
    identificacion_titular  text,
    nombre_titular          text,
    nombre_establecimiento  text,
    direccion               text,
    telefono                text,
    telefono2               text,
    regimen                 text,
    facturador_electronico  text,
    residente               text,
    correo                  text,
    ciudad                  text,
    zona                    text,
    gestor                  text,               -- nombre o id del gestor, sin llave foránea a propósito
                                                  -- (así una carga con datos inconsistentes no se rompe)
    estado                  text default 'Activo',
    fecha_actualizacion     timestamptz default now(),
    latitud_referencia      double precision,   -- última posición GPS confirmada en visita
    longitud_referencia     double precision
);

-- 3) PREGUNTAS_VISITA (catálogo dinámico del acta) ---------------------------
create table if not exists preguntas_visita (
    id_pregunta     text primary key,          -- P001, P002, ...
    seccion         text not null,             -- 1..8 = corresponsal, OF = oficina
    pregunta        text not null,
    tiporespuesta   text not null,             -- Texto, Texto largo, Si/No, Opcion multiple, Seleccion multiple
    opciones        text,                      -- choices separados por " | "
    obligatoria     text default 'Si',
    activo          text default 'Si',
    orden           integer not null,
    aplica_visita   text not null default 'Prospección, Seguimiento'  -- Prospección, Seguimiento, Oficina (o combinación separada por coma)
);

-- 4) ACTAS_VISITA (encabezado de cada visita) --------------------------------
create table if not exists actas_visita (
    id_acta         bigserial primary key,
    pds             text,               -- sin llave foránea: en Prospección el PDS puede ser nuevo
                                          -- y aún no existir en la tabla pds
    gestor          text,
    fecha_visita    date not null default current_date,
    hora_inicio     time,
    hora_fin        time,
    latitud         double precision,
    longitud        double precision,
    precision_gps   double precision,          -- metros (accuracy del GPS del dispositivo)
    distancia_pds   double precision,          -- metros entre el GPS de la visita y el PDS registrado
    tipo_visita     text not null,             -- Prospección | Seguimiento | Oficina
    estado_visita   text default 'Completa',
    observaciones   text,
    creado_en       timestamptz default now()
);

-- 5) RESPUESTAS_VISITA (una fila por pregunta respondida) --------------------
create table if not exists respuestas_visita (
    id              bigserial primary key,
    id_acta         bigint references actas_visita(id_acta) on delete cascade,
    id_pregunta     text,               -- referencia lógica a preguntas_visita.id_pregunta
    respuesta       text,
    observacion     text
);

-- 6) EVIDENCIAS_VISITA (fotos, referenciando el bucket de Storage) -----------
create table if not exists evidencias_visita (
    id              bigserial primary key,
    id_acta         bigint references actas_visita(id_acta) on delete cascade,
    tipo            text,                      -- Fachada, Interior, Documento, etc.
    nombre_archivo  text,
    ruta_archivo    text,                      -- ruta dentro del bucket de Supabase Storage
    url_publica     text,                      -- URL pública devuelta por Supabase Storage
    fecha           timestamptz default now(),
    latitud         double precision,
    longitud        double precision
);

-- 7) CAMBIOS_PDS (bitácora de auditoría — nunca se sobreescribe PDS directo) --
create table if not exists cambios_pds (
    id                      bigserial primary key,
    pds                     text,
    campo_modificado        text not null,
    valor_anterior          text,
    valor_nuevo             text,
    gestor                  text,
    fecha_cambio            timestamptz default now(),
    motivo                  text,
    estado_sincronizacion   text default 'Pendiente'  -- Pendiente | Aplicado
);

-- Índices para las consultas más frecuentes del backend -----------------------
create index if not exists idx_pds_gestor on pds(gestor);
create index if not exists idx_actas_pds on actas_visita(pds);
create index if not exists idx_actas_gestor on actas_visita(gestor);
create index if not exists idx_actas_fecha on actas_visita(fecha_visita);
create index if not exists idx_respuestas_acta on respuestas_visita(id_acta);
create index if not exists idx_evidencias_acta on evidencias_visita(id_acta);
create index if not exists idx_cambios_pds on cambios_pds(pds);
