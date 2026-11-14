import L from "leaflet";
import { useEffect } from "react";
import { Circle, MapContainer, Marker, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import { CENTRO_SANTA_MARTA, URGENCIA } from "../constantes.js";
import { svgCategoria } from "../iconos.jsx";

// Marcadores con el ícono de la categoría (Phosphor) y borde del color de la urgencia
const cacheIconos = {};
export function iconoReporte(r, seleccionado = false) {
  const clave = `${r.categoria}-${r.urgencia}-${seleccionado}-${r.estado}`;
  if (!cacheIconos[clave]) {
    const color = URGENCIA[r.urgencia]?.color || "#566778";
    cacheIconos[clave] = L.divIcon({
      className: "",
      html: `<div class="pin ${seleccionado ? "pin-sel" : ""} ${r.estado === "en_atencion" ? "pin-atencion" : ""}" style="border-color:${color}">${svgCategoria(r.categoria, color)}</div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    });
  }
  return cacheIconos[clave];
}

function Enfocar({ punto }) {
  const mapa = useMap();
  useEffect(() => {
    if (punto) mapa.flyTo(punto, Math.max(mapa.getZoom(), 15), { duration: 0.6 });
  }, [punto, mapa]);
  return null;
}

function Clics({ onClic }) {
  useMapEvents({ click: (e) => onClic?.([e.latlng.lat, e.latlng.lng]) });
  return null;
}

export const CAPA_MAPA = {
  // Teselas estándar de OpenStreetMap: no requieren API key (CARTO ahora la exige)
  url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  maxZoom: 19,
};

export default function MapaReportes({ reportes, seleccionado, onSeleccionar, circulo, onClicMapa, enfocar }) {
  return (
    <MapContainer center={CENTRO_SANTA_MARTA} zoom={13} className="mapa" scrollWheelZoom>
      <TileLayer {...CAPA_MAPA} />
      {reportes.map((r) => (
        <Marker key={r.id} position={[r.lat, r.lng]} icon={iconoReporte(r, r.id === seleccionado)}
                eventHandlers={{ click: () => onSeleccionar(r.id) }}>
          <Tooltip direction="top" offset={[0, -16]}>{r.subtipo_nombre}, {r.barrio}</Tooltip>
        </Marker>
      ))}
      {reportes.filter((r) => r.ubicacion_aproximada).map((r) => (
        <Circle key={`c-${r.id}`} center={[r.lat, r.lng]} radius={150}
                pathOptions={{ color: "#E8553A", weight: 1, fillOpacity: 0.06, dashArray: "4" }} />
      ))}
      {circulo && <Circle center={circulo.centro} radius={circulo.km * 1000}
                          pathOptions={{ color: "#0B4F6C", weight: 2, fillOpacity: 0.05 }} />}
      <Clics onClic={onClicMapa} />
      <Enfocar punto={enfocar} />
    </MapContainer>
  );
}
