# -*- coding: utf-8 -*-
"""
Catálogo de nombres de oficina, para el autocompletar de "Nombre de la
oficina" cuando el tipo de visita es "Oficina" (antes era un campo de
texto libre, lo que generaba nombres inconsistentes entre visitas).

NOTA: esta es la lista BORRADOR que Daya compartió (16-sep-2026), sin
editar todavía — ella avisó que venían más cambios y que consolidaría
la versión final. En cuanto la envíe, se reemplaza esta lista (o se
migra a una tabla en Supabase si el catálogo empieza a necesitar más
que solo el nombre, p. ej. ciudad o código de oficina).
"""

OFICINAS = [
    "Acacías", "Alamos", "Alcázares", "Alegra", "Alfonso López", "Altavista",
    "Alto Prado", "América", "Apartadó", "Arauca", "Armenia Plaza", "Asturias",
    "Avenida 26", "Avenida 30 de Agosto", "Avenida 40", "Avenida Caracas",
    "Avenida Cero", "Avenida Chile", "Avenida Ciudad de Cali", "Avenida Colombia",
    "Avenida Cuarta Cúcuta", "Avenida El Dorado", "Avenida Estacion",
    "Avenida Las Palmas Fusagasugá", "Avenida Los Estudiantes",
    "Avenida Norte Tunja", "Avenida Oriental", "Avenida Quinta",
    "Avenida Santander", "Barrancabermeja", "Barranquilla", "Belén", "Bello",
    "Bosa", "Bosa Centro", "Bosa La Grande (Extensión Bosa)", "Bosa Porvenir",
    "Boulevard 58", "Bucaramanga principal", "Buenaventura", "Buga",
    "Cabecera del llano", "Cajicá", "Caldas", "Calima", "Calle 10 Cúcuta",
    "Calle 100", "Calle 12", "Calle 20 Pasto", "Calle 21 Armenia", "Calle 72",
    "Calle 80", "Calle Novena", "Calle Sarmiento Tulua", "Cañaveral",
    "Carrera 25 Pasto", "Carrera 27 Palmira", "Carrera 3 La Dorada",
    "Carrera 33", "Carrera 70", "Carrera Décima", "Cartagena", "Cartago",
    "Casablanca", "Castellana", "Castilla", "Cedritos", "Central Mayorista",
    "Centro Andino", "Centro Coltejer", "Centro Comercial Galerías",
    "Centro Comercial Mayorca", "Centro Comercial Niza",
    "Centro Empresarial Calle 26", "Centro Mayor", "Centro Suba", "Cereté",
    "Chapinero", "Chía", "Chico", "Chinchiná", "Chipichape", "Chiquinquirá",
    "Ciudad Montes", "Ciudad Tunal", "Ciudad Verde", "Colina Campestre",
    "Contador", "Corabastos", "Cosmocentro", "Cuba", "Diverplaza",
    "Dosquebradas", "El Edén", "El Ensueño", "El Jordán", "Envigado",
    "Espinal", "Estrada", "Extensión San Martín", "Facatativá", "Florencia",
    "Floresta", "Florida", "Funza", "Fusagasugá", "Garzón", "Gilberto Alzate",
    "Girardot 2", "Girón", "Granada", "Guacarí", "Hayuelos", "Honda",
    "Ingles", "Ipiales", "Itagüí", "Itagüí Cll 50", "Jardín Plaza", "Kennedy",
    "Kennedy Plaza", "La Casona", "La Catedral", "La Ermita", "La Esmeralda",
    "La Felicidad", "La Gaitana", "La Independencia", "La Luna", "La Matuna",
    "La Mesa", "La Triada", "La Victoria", "La Virginia", "Las Aguas",
    "Las Ferias", "Los Molinos", "Los Sauces", "Madrid", "Manrique",
    "Mariquita", "Marly", "Melgar", "Mercurio", "Metrocentro", "Metrópolis",
    "Modelia", "Montería", "Mosquera", "Neiva", "Nogal", "Ocaña", "Pablo VI",
    "Park Way", "Parque Berrio", "Parque Caldas", "Parque de la Villa Sogamoso",
    "Parque Fabricato", "Parque Fontibón", "Parque la Arboleda",
    "Parque la Colina", "Parque Libertadores Duitama", "Parque Nacional",
    "Paseo Villa del Rio", "Pastranita", "Patio Bonito", "Pepe Sierra",
    "Pereira", "Piedecuesta", "Pitalito", "Plaza Boyacá Tulua",
    "Plaza de Bolivar", "Plaza de las Américas", "Plaza Imperial",
    "Plazoleta Centauros Villavicencio", "Plazoleta Plaza de las Américas",
    "Poblado", "Popayán", "Portal de La 80", "Portal del Prado",
    "Prado Veraniego", "Primavera", "Puente Largo", "Puerta del Norte",
    "Quinta Paredes", "Quirigua", "Quirinal", "Quiroga", "Restrepo",
    "Restrepo Valvanera", "Ricaurte", "Rincón de Suba", "Rionegro",
    "Ronda Real", "Salitre", "San Andrés", "San Cristobal", "San Diego",
    "San Francisco", "San Gil", "San Ignacio", "San Martín", "Santa Bárbara",
    "Santa Helenita", "Santa Isabel", "Santa Librada", "Santa Lucía",
    "Santa Marta", "Santafé", "Soacha Parque", "Soledad", "Tabora", "Tejar",
    "Teleport", "Terminal de Transporte", "Tesoro", "Tintal", "Titán",
    "Toberín", "Trinidad Galán", "Troncal", "Tunja", "Túquerres", "Unicentro",
    "Unicentro Cali", "Unicentro Cúcuta", "Unicentro Medellín", "Unisur",
    "Valledupar", "Veinte de Julio", "Veinte de Julio Cra 5", "Venecia",
    "Venecia Av. 68", "Ventura Terreros", "Villa Javier", "Yopal",
    "Zipaquirá", "Zona Industrial",
]


def listar_oficinas() -> list[str]:
    return sorted(OFICINAS)
