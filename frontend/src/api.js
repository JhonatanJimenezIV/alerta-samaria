// Cliente del API. Todas las rutas pasan por el proxy de Vite (/api → API Gateway).
const BASE = "/api";

export class ErrorApi extends Error {
  constructor(status, mensaje) {
    super(mensaje);
    this.status = status;
  }
}

function usuarioGuardado() {
  try {
    return JSON.parse(localStorage.getItem("alerta-samaria:sesion") || "null");
  } catch {
    return null;
  }
}

export async function api(ruta, { metodo = "GET", body, usuarioId } = {}) {
  const headers = { "Content-Type": "application/json" };
  const id = usuarioId ?? usuarioGuardado()?.id;
  if (id) headers["X-Usuario-Id"] = id;
  let resp;
  try {
    resp = await fetch(BASE + ruta, { method: metodo, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new ErrorApi(0, "No hay conexión con el API. ¿Está corriendo el emulador y el deploy?");
  }
  const texto = await resp.text();
  // Si el emulador se reinició, el api-id ya no existe: LocalStack responde con XML de S3
  // ("NoSuchBucket ... restapis") o con "does not correspond to a deployed API".
  if (/NoSuchBucket|does not correspond to a deployed API/.test(texto)) {
    throw new ErrorApi(503, "El API no está desplegado en el emulador (suele pasar después de reiniciar Docker). En cdk-dev ejecuta bash scripts/deploy.sh y python scripts/seed.py, y luego reinicia npm run dev.");
  }
  let datos = {};
  try {
    datos = texto ? JSON.parse(texto) : {};
  } catch {
    datos = { error: texto };
  }
  if (!resp.ok) throw new ErrorApi(resp.status, datos.error || datos.message || `Error ${resp.status}`);
  return datos;
}

export const qs = (params) => {
  const p = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return p.length ? "?" + new URLSearchParams(p).toString() : "";
};

// Sube un archivo directo a S3 con la URL prefirmada que entrega el API (PUT).
// Se usa XMLHttpRequest porque fetch no informa el progreso de subida.
export function subirArchivo(url, archivo, contentType, alProgresar) {
  return new Promise((resolver, rechazar) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", contentType);
    xhr.upload.onprogress = (e) => e.lengthComputable && alProgresar?.(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolver() : rechazar(new ErrorApi(xhr.status, `S3 respondió ${xhr.status} al subir ${archivo.name}`)));
    xhr.onerror = () => rechazar(new ErrorApi(0, `No se pudo subir ${archivo.name}. Revisa que el emulador esté corriendo`));
    xhr.send(archivo);
  });
}

// Flujo completo de un adjunto: pedir URL → subir a S3 → confirmar
export async function adjuntarArchivo(reporteId, archivo, alProgresar) {
  const contentType = archivo.type || "application/octet-stream";
  const pedido = await api(`/reportes/${reporteId}/media`, { metodo: "POST", body: { content_type: contentType, tamano: archivo.size } });
  await subirArchivo(pedido.url_subida, archivo, contentType, alProgresar);
  return api(`/reportes/${reporteId}/media/${pedido.id}/confirmar`, { metodo: "POST", body: {} });
}
