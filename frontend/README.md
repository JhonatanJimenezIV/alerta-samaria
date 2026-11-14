# Frontend — Alerta Samaria (React + Vite + Leaflet)

Requisito: Node.js 18 o superior en tu máquina (`node -v`).

```powershell
cd frontend
npm install        # solo la primera vez
npm run dev        # abre http://localhost:5173
```

- La URL del API la escribe `bash scripts/deploy.sh` en `.env.local`. Si vuelves a desplegar
  (cambia el api-id), **reinicia `npm run dev`** para que tome la nueva URL.
- Vite reenvía `/api/*` al API Gateway del emulador (ver `vite.config.js`), así el navegador
  no hace peticiones cross-origin.
- `python scripts/seed.py` deja los usuarios de prueba en `public/usuarios_demo.json`; aparecen
  en la pantalla **Ingresar**.

| Pantalla | Qué muestra | Patrones |
|---|---|---|
| Mapa (`/`) | Feed en vivo (se refresca cada 15 s), cerca de mí, filtros, detalle, ranking | AP1–AP6, AP10, AP12 |
| Reportar | Formulario con GPS, pin arrastrable y barrio sugerido | AP9 |
| Mis reportes | Reportes del ciudadano | AP11 |
| Panel de entidad | Pendientes por urgencia, detalle completo, cambio de estado, estadísticas y riesgo | AP13–AP17 |

Cada respuesta muestra una insignia **⚡ Redis (caché)** o **🗄️ DynamoDB** según el campo `_fuente`.
