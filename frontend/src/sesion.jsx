// Sesión simplificada del proyecto: se guarda el usuario y se envía su id en X-Usuario-Id.
import { createContext, useContext, useState } from "react";

const Contexto = createContext(null);
const CLAVE = "alerta-samaria:sesion";

function leer() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE) || "null");
  } catch {
    return null;
  }
}

export function ProveedorSesion({ children }) {
  const [usuario, setUsuario] = useState(leer);

  const iniciar = (u) => {
    try { localStorage.setItem(CLAVE, JSON.stringify(u)); } catch { /* sin almacenamiento */ }
    setUsuario(u);
  };
  const cerrar = () => {
    try { localStorage.removeItem(CLAVE); } catch { /* sin almacenamiento */ }
    setUsuario(null);
  };
  return <Contexto.Provider value={{ usuario, iniciar, cerrar }}>{children}</Contexto.Provider>;
}

export const useSesion = () => useContext(Contexto);
