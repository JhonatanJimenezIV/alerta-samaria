"""
catalogo.py — Catálogo de categorías (AP6).

El catálogo es un DATO, no código: vive en DynamoDB (PK=CONFIG, SK=CATEGORIAS)
y se cachea en Redis (cfg:categorias, TTL 24 h) con Cache-Aside. Este archivo
solo trae la versión inicial, que scripts/seed.py carga en la tabla y que se usa
como respaldo si la tabla todavía no lo tiene.

urgencia: 1 = alta, 2 = media, 3 = baja · horas: tiempo activo en el feed/mapa
"""
from typing import Any

from comun import cache, db

CLAVE_CACHE = "cfg:categorias"


def _s(id_: str, nombre: str, urgencia: int, horas: int, afecta: list[str] | None = None) -> dict[str, Any]:
    return {"id": id_, "nombre": nombre, "urgencia": urgencia, "horas": horas, "tambien_afecta": afecta or []}


CATALOGO_INICIAL: dict[str, Any] = {
    "version": 1,
    "categorias": [
        {"id": "emergencias", "nombre": "Emergencias", "icono": "🔥", "aviso_123": True,
         "ubicacion_aproximada": False, "subtipos": [
            _s("incendio_estructural", "Incendio estructural", 1, 6),
            _s("incendio_forestal", "Incendio forestal en cerros o la Sierra", 1, 12, ["ambiente"]),
            _s("cable_caido", "Cable eléctrico caído o poste en riesgo", 1, 12, ["servicios"]),
            _s("fuga_gas", "Fuga de gas", 1, 6, ["servicios"]),
            _s("accidente_heridos", "Accidente con heridos", 1, 6, ["transito"]),
        ]},
        {"id": "seguridad", "nombre": "Seguridad", "icono": "🚨", "aviso_123": True,
         "ubicacion_aproximada": True, "subtipos": [
            _s("robo", "Robo o atraco", 1, 24),
            _s("rina_disturbio", "Riña o disturbio", 1, 24),
            _s("actividad_sospechosa", "Actividad sospechosa", 1, 24),
            _s("zona_oscura", "Zona sola y oscura", 2, 168),
        ]},
        {"id": "servicios", "nombre": "Servicios públicos", "icono": "💧", "aviso_123": False,
         "ubicacion_aproximada": False, "subtipos": [
            _s("sin_agua", "Sin agua", 2, 72),
            _s("carrotanque", "Carrotanque no llegó", 2, 72),
            _s("tuberia_rota", "Tubería rota", 2, 72, ["vias"]),
            _s("alcantarilla_rebosada", "Alcantarilla rebosada", 2, 72, ["vias", "ambiente"]),
            _s("sin_luz", "Sin luz o apagón", 2, 72),
            _s("alumbrado_danado", "Alumbrado público dañado", 2, 168, ["seguridad"]),
            _s("sin_gas", "Sin gas", 2, 72),
        ]},
        {"id": "vias", "nombre": "Vías", "icono": "🌧️", "aviso_123": False,
         "ubicacion_aproximada": False, "subtipos": [
            _s("calle_inundada", "Calle inundada", 1, 12),
            _s("arroyo", "Arroyo peligroso", 1, 12),
            _s("derrumbe", "Derrumbe o deslizamiento", 1, 24),
            _s("via_cerrada", "Vía cerrada", 2, 168),
            _s("hueco", "Hueco", 2, 168),
            _s("tapa_alcantarilla", "Tapa de alcantarilla robada o faltante", 2, 168),
        ]},
        {"id": "transito", "nombre": "Tránsito", "icono": "🚦", "aviso_123": False,
         "ubicacion_aproximada": False, "subtipos": [
            _s("accidente", "Accidente sin heridos", 2, 6),
            _s("trancon", "Trancón fuerte", 2, 6),
            _s("semaforo_danado", "Semáforo dañado", 3, 168),
            _s("mal_parqueado", "Vehículo mal parqueado que bloquea", 3, 168),
        ]},
        {"id": "ambiente", "nombre": "Ambiente y salud pública", "icono": "🗑️", "aviso_123": False,
         "ubicacion_aproximada": False, "subtipos": [
            _s("basura", "Basura acumulada", 3, 72),
            _s("aguas_estancadas", "Aguas estancadas o criaderos de mosquitos", 2, 72),
            _s("quema_basura", "Quema de basura", 2, 72),
            _s("arbol_caido", "Árbol caído", 2, 72, ["vias"]),
            _s("ruido", "Ruido excesivo o picó", 3, 72),
        ]},
        {"id": "animales", "nombre": "Animales", "icono": "🐕", "aviso_123": False,
         "ubicacion_aproximada": False, "subtipos": [
            _s("animal_herido", "Animal herido o atropellado", 2, 72),
            _s("perro_agresivo", "Perro agresivo suelto", 2, 72),
            _s("maltrato_animal", "Maltrato animal", 2, 72),
        ]},
        {"id": "playas", "nombre": "Playas y espacio público", "icono": "🏖️", "aviso_123": False,
         "ubicacion_aproximada": False, "subtipos": [
            _s("playa_contaminada", "Playa contaminada o con vertimientos", 3, 168),
            _s("mar_peligroso", "Mar peligroso", 3, 168),
            _s("anden_invadido", "Andén invadido", 3, 168),
            _s("parque_deteriorado", "Parque deteriorado", 3, 168),
        ]},
        {"id": "otro", "nombre": "Otro", "icono": "❓", "aviso_123": False,
         "ubicacion_aproximada": False, "subtipos": [
            _s("otro", "Otro (sujeto a moderación)", 3, 24),
        ]},
    ],
}


def obtener() -> tuple[dict[str, Any], str]:
    """Cache-Aside: Redis → DynamoDB → catálogo inicial. Devuelve (catálogo, fuente)."""
    en_cache = cache.get_json(CLAVE_CACHE)
    if en_cache:
        return en_cache, "cache"
    item = db.tabla().get_item(Key={"PK": "CONFIG", "SK": "CATEGORIAS"}).get("Item")
    if item:
        datos = db.desde_dynamo({"version": item.get("version", 1), "categorias": item["categorias"]})
        fuente = "dynamodb"
    else:
        datos, fuente = CATALOGO_INICIAL, "inicial"
    cache.set_json(CLAVE_CACHE, datos, cache.TTL_CATALOGO)
    return datos, fuente


def buscar(categoria_id: str, subtipo_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Valida categoría/subtipo y devuelve (categoría, subtipo)."""
    datos, _ = obtener()
    for cat in datos["categorias"]:
        if cat["id"] == categoria_id:
            for sub in cat["subtipos"]:
                if sub["id"] == subtipo_id:
                    return cat, sub
    return None


def nombres(categoria_id: str, subtipo_id: str) -> tuple[str, str]:
    encontrado = buscar(categoria_id, subtipo_id)
    if not encontrado:
        return categoria_id, subtipo_id
    return encontrado[0]["nombre"], encontrado[1]["nombre"]
