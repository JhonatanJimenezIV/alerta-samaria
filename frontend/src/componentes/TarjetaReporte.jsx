import { UsersThree } from "@phosphor-icons/react";
import { haceCuanto } from "../constantes.js";
import { IconoCategoria } from "../iconos.jsx";
import { Estado, Urgencia } from "./Insignias.jsx";

function distancia(km) {
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
}

export default function TarjetaReporte({ reporte: r, onClick, seleccionado, extra }) {
  return (
    <button className={`tarjeta ${seleccionado ? "activa" : ""}`} onClick={onClick}>
      <span className={`tarjeta-icono u${r.urgencia}`}><IconoCategoria categoria={r.categoria} size={20} /></span>
      <span className="tarjeta-cuerpo">
        <span className="tarjeta-titulo">{r.subtipo_nombre || r.titulo}</span>
        <span className="tarjeta-meta" style={{ display: "block" }}>
          {r.barrio}, {haceCuanto(r.creado_en)}{r.distancia_km !== undefined && `, a ${distancia(r.distancia_km)}`}
        </span>
        <span className="tarjeta-insignias">
          <Urgencia nivel={r.urgencia} />
          <Estado estado={r.estado} />
          {r.confirmaciones > 0 && <span className="confirmaciones"><UsersThree size={14} weight="bold" />{r.confirmaciones}</span>}
          {extra}
        </span>
      </span>
    </button>
  );
}
