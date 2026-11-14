# Alerta Samaria

Plataforma serverless de reportes ciudadanos para Santa Marta: robos, daños de servicios públicos,
vías inundadas, semáforos dañados, incendios, etc.
Proyecto final de **Bases de Datos NoSQL** (DynamoDB + Redis), construido sobre el
[proyecto base del curso](https://gitlab.com/caov_unimag/bd_no_sql).

| Pieza | Tecnología |
|---|---|
| Base de datos (fuente de verdad) | DynamoDB, **tabla única** con PK/SK, 4 GSI y TTL |
| Caché / tiempo real | Redis 7: feed (Sorted Set), cercanía (GEO), ranking, rate limiting, Cache-Aside |
| Fotos y videos | S3 (emulado): el navegador sube directo con URLs prefirmadas; DynamoDB guarda la referencia |
| Backend | 4 Lambdas Python 3.11 detrás de API Gateway |
| Infraestructura | AWS CDK (Python) + `cdklocal` sobre LocalStack 4.14 o MiniStack |
| Entorno | Docker Compose: `emulador` + `redis` + `cdk-dev` |
| Frontend | React + Vite + Leaflet (carpeta `frontend/`, ver su README) |

## Puesta en marcha

Requisito: **Docker Desktop** abierto. Desde esta carpeta:

```bash
# 1. Levantar los 3 contenedores (la primera vez tarda unos minutos)
docker compose up -d --build

# 2. Entrar al contenedor de desarrollo
docker compose exec cdk-dev bash

# 3. (dentro de cdk-dev) Desplegar: bootstrap + deploy + URLs
bash scripts/deploy.sh

# 4. (dentro de cdk-dev) Cargar datos de demostración
python scripts/seed.py

# 5. (dentro de cdk-dev) Ejecutar los tests (no necesitan el emulador)
python -m pytest tests/ -v
```

> ⚠️ Después de cada reinicio del contenedor `emulador` hay que repetir los pasos 3 y 4:
> LocalStack Community no guarda estado y el `api-id` cambia.

Luego, en **otra terminal de PowerShell** (fuera del contenedor), el frontend:

```powershell
cd frontend
npm install      # solo la primera vez
npm run dev      # http://localhost:5173
```

`deploy.sh` imprime la URL base, de la forma
`http://localhost:4566/restapis/<api-id>/prod/_user_request_`, y la escribe en `frontend/.env.local`.

## Endpoints

Autenticación simplificada: el header `X-Usuario-Id` identifica al usuario
(los ids de prueba quedan en `app/scripts/usuarios_demo.json` después del seed).

| Método | Ruta | AP | Requiere |
|---|---|---|---|
| GET | `/health` | — | — |
| GET | `/reportes/feed?limite=&categoria=` | AP1 | — |
| GET | `/reportes/cerca?lat=&lng=&km=` | AP2 | — |
| GET | `/reportes/{id}` | AP3, AP12 | — |
| GET | `/barrios/{barrio}/reportes` | AP4 | — |
| GET | `/ranking/barrios` | AP5 | — |
| GET | `/categorias` | AP6 | — |
| POST | `/usuarios` | AP7 | — |
| GET | `/usuarios/{id}` | AP8 | ciudadano (el mismo) |
| POST | `/reportes` | AP9 | ciudadano |
| POST | `/reportes/{id}/confirmaciones` | AP10 | ciudadano |
| GET | `/usuarios/{id}/reportes` | AP11 | ciudadano (el mismo) |
| GET | `/entidad/reportes?categoria=&estado=` | AP13 | entidad |
| GET | `/entidad/reportes/{id}` | AP14 | entidad |
| PATCH | `/entidad/reportes/{id}/estado` | AP15 | entidad |
| GET | `/entidad/estadisticas?fecha=AAAA-MM-DD` | AP16 | entidad |
| GET | `/entidad/riesgo/{barrio}?desde=&hasta=` | AP17 | entidad |
| POST | `/reportes/{id}/media` | AP21 | autor del reporte |
| POST | `/reportes/{id}/media/{mid}/confirmar` | AP22 | autor del reporte |
| GET | `/videos` | AP23 | — |

Las respuestas de lectura incluyen `"_fuente": "cache"` o `"dynamodb"` para evidenciar el caché.

### Ejemplos con curl (desde tu máquina)

```bash
BASE=http://localhost:4566/restapis/<api-id>/prod/_user_request_

curl $BASE/reportes/feed
curl "$BASE/reportes/cerca?lat=11.193&lng=-74.224&km=2"

# Crear un reporte (usa un id de ciudadano de usuarios_demo.json)
curl -X POST $BASE/reportes -H "Content-Type: application/json" -H "X-Usuario-Id: <id>" \
  -d '{"categoria":"vias","subtipo":"calle_inundada","lat":11.2420,"lng":-74.2110,
       "barrio":"Centro Histórico","descripcion":"Calle inundada por el aguacero"}'

# Panel de una entidad
curl "$BASE/entidad/reportes?categoria=servicios" -H "X-Usuario-Id: ENT-SERVICIOS"
```

### Ver Redis

```bash
docker compose exec redis redis-cli ZREVRANGE feed:ciudad 0 -1
docker compose exec redis redis-cli KEYS '*'
```

## Estructura

```
alerta-samaria/
├── docker-compose.yml        # emulador + redis + cdk-dev (red fija alerta-samaria-net)
├── Dockerfile                # imagen de cdk-dev
├── frontend/                 # React + Vite + Leaflet (mapa, reportar, panel de entidad)
└── app/
    ├── infra/stack.py        # tabla + 4 GSI + TTL, 4 Lambdas, API Gateway con CORS
    ├── lambdas/src/
    │   ├── reportes.py       # AP1–AP6, AP9, AP10
    │   ├── usuarios.py       # AP7, AP8, AP11
    │   ├── entidad.py        # AP13–AP17
    │   ├── health.py
    │   └── comun/            # db, cache (Redis), catálogo, modelo (privacidad), estados, http
    ├── scripts/              # deploy.sh, post_deploy.py, seed.py
    └── tests/                # pytest + moto + fakeredis (28 tests)
```

## Decisiones clave (resumen para la sustentación)

- **Single Table Design**: reporte, historial y confirmaciones comparten la partición `REP#<id>`;
  un solo `Query` trae todo. Ningún patrón usa `Scan`.
- **DynamoDB guarda todo el histórico; Redis solo lo activo.** Cada subtipo define cuántas horas
  permanece en el feed/mapa (una calle inundada 12 h, un semáforo 7 días).
- **Cache-Aside** en detalle y catálogo, **Write-Through** al crear (feed, GEO, ranking),
  **invalidación** al cambiar de estado.
- **Transacciones** solo donde hay invariantes: correo único, un voto por usuario y cambio de
  estado + evento.
- **Modo degradado**: si Redis cae, el feed y la cercanía se sirven desde GSI4.
- **TTL**: un reporte que nadie confirma en 48 h se elimina solo.
- **Fotos y videos sin pasar por la Lambda**: URL prefirmada de S3 → subida directa → confirmación
  (HeadObject). El ítem `MEDIA#` vive en la partición del reporte y los videos sobrecargan el GSI4
  (`MEDIA#<fecha>`) como respaldo del feed de `/videos` en Redis. En Seguridad no se permiten adjuntos.
- **Privacidad por niveles** (Ley 1581 de 2012): en Seguridad la ubicación pública es aproximada
  (~150 m) y nunca se publican datos del reportante.
