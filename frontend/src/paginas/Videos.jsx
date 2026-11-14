import { FilmStrip, MapPin, Plus } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { haceCuanto } from "../constantes.js";
import { Fuente, Urgencia } from "../componentes/Insignias.jsx";
import { IconoCategoria } from "../iconos.jsx";
import { Credito } from "../componentes/Galeria.jsx";
import PaginaHero from "../componentes/PaginaHero.jsx";

export default function Videos() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api("/videos?limite=30").then(setDatos).catch((e) => setError(e.message)); }, []);

  return (
    <>
    <PaginaHero foto="taganga" titulo="Videos de lo que pasa ahora"
                texto="Clips que los vecinos graban y adjuntan a sus reportes: un arroyo crecido, un incendio en los cerros, una vía cerrada.">
      {datos && <Fuente fuente={datos._fuente} />}
    </PaginaHero>
    <div className="pagina superpuesta">
      {error && <p className="error">{error}</p>}
      {!datos && !error && (
        <div className="videos-grid">{[0, 1, 2].map((i) => <div key={i} className="esqueleto" style={{ aspectRatio: "16 / 10" }} />)}</div>
      )}
      {datos?.total === 0 && (
        <div className="caja estado-vacio">
          <div>
            <div className="icono-grande"><FilmStrip size={32} weight="bold" /></div>
            <h2>Todavía no hay videos</h2>
            <p>Cuando alguien adjunte un video a su reporte, aparecerá aquí. Puedes ser el primero.</p>
            <Link to="/reportar" className="boton atardecer"><Plus size={18} weight="bold" />Reportar con video</Link>
          </div>
        </div>
      )}
      {datos?.total > 0 && (
        <div className="videos-grid">
          {datos.videos.map((v) => (
            <article key={v.id} className="video-tarjeta">
              <video src={v.url} controls playsInline preload="metadata" aria-label={`Video: ${v.subtipo_nombre} en ${v.barrio}`} />
              <div className="video-info">
                <span className={`tarjeta-icono u${v.urgencia}`}><IconoCategoria categoria={v.categoria} size={20} /></span>
                <div>
                  <h2>{v.subtipo_nombre}</h2>
                  <p className="nota">{v.barrio}, {haceCuanto(v.creado_en)}</p>
                </div>
              </div>
              {v.credito && <div style={{ padding: "0 16px" }}><Credito credito={v.credito} /></div>}
              <div className="video-pie">
                <Urgencia nivel={v.urgencia} />
                <Link to={`/mapa?r=${v.rid}`} className="enlace"><MapPin size={16} weight="bold" />Ver en el mapa</Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
    </>
  );
}
