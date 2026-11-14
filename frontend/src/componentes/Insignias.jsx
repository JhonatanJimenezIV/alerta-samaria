import { Database, Lightning } from "@phosphor-icons/react";
import { ESTADOS, URGENCIA } from "../constantes.js";

export function Urgencia({ nivel }) {
  const u = URGENCIA[nivel] || URGENCIA[3];
  return <span className={`insignia u${nivel}`}>Urgencia {u.nombre.toLowerCase()}</span>;
}

export function Estado({ estado }) {
  return <span className={`insignia estado ${estado}`}>{ESTADOS[estado]?.nombre || estado}</span>;
}

// De dónde vino la respuesta: evidencia el caché en la demo
export function Fuente({ fuente }) {
  if (!fuente) return null;
  const esCache = fuente === "cache";
  return (
    <span className={`fuente ${esCache ? "cache" : "dynamo"}`} title="Origen de los datos de esta respuesta">
      {esCache ? <Lightning size={14} weight="fill" /> : <Database size={14} weight="fill" />}
      {esCache ? "Redis (caché)" : "DynamoDB"}
    </span>
  );
}
