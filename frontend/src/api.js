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
