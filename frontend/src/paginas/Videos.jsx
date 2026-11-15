import { FilmStrip, MapPin, Play, Plus, Eye } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { haceCuanto } from "../constantes.js";
import { Fuente, Urgencia } from "../componentes/Insignias.jsx";
import { IconoCategoria } from "../iconos.jsx";
import { Credito } from "../componentes/Galeria.jsx";
import PaginaHero from "../componentes/PaginaHero.jsx";

function VideoDestacado({ v }) {
  const [play, setPlay] = useState(false);
  return (
    <section className="vid-destacado">
      <div className="vid-destacado-player">
        {!play && (
          <button className="vid-play-overlay" onClick={() => setPlay(true)} aria-label="Reproducir video">
            <span className="vid-play-btn"><Play size={32} weight="fill" /></span>
          </button>
        )}
        <video src={v.url} controls={play} autoPlay={play} playsInline preload="metadata"
               aria-label={`Video: ${v.subtipo_nombre} en ${v.barrio}`}
               onClick={() => !play && setPlay(true)} />
      </div>
      <div className="vid-destacado-info">
        <div className="vid-destacado-badge">
          <span className="vid-cat-icon"><IconoCategoria categoria={v.categoria} size={20} /></span>
          <Urgencia nivel={v.urgencia} />
        </div>
        <h2>{v.subtipo_nombre}</h2>
        <p className="vid-ubicacion"><MapPin size={16} weight="bold" />{v.barrio} · {haceCuanto(v.creado_en)}</p>
        {v.descripcion && <p className="vid-desc">{v.descripcion}</p>}
        {v.credito && <Credito credito={v.credito} />}
        <div className="vid-acciones">
          <Link to={`/mapa?r=${v.rid}`} className="boton primario pequeno"><MapPin size={16} weight="bold" />Ver en el mapa</Link>
          <Link to={`/mapa?r=${v.rid}`} className="boton pequeno"><Eye size={16} weight="bold" />Ver reporte</Link>
        </div>
      </div>
    </section>
  );
}

function VideoFila({ v }) {
  return (
    <article className="vid-fila">
      <div className="vid-fila-player">
        <video src={v.url} controls playsInline preload="metadata"
               aria-label={`Video: ${v.subtipo_nombre} en ${v.barrio}`} />
      </div>
      <div className="vid-fila-info">
        <div className="vid-fila-cab">
          <span className={`tarjeta-icono u${v.urgencia}`}><IconoCategoria categoria={v.categoria} size={20} /></span>
          <div>
            <h3>{v.subtipo_nombre}</h3>
            <p className="vid-fila-meta"><MapPin size={14} weight="bold" />{v.barrio} · {haceCuanto(v.creado_en)}</p>
          </div>
        </div>
        {v.descripcion && <p className="vid-fila-desc">{v.descripcion}</p>}
        {v.credito && <div className="vid-fila-credito"><Credito credito={v.credito} /></div>}
        <div className="vid-fila-pie">
          <Urgencia nivel={v.urgencia} />
          <Link to={`/mapa?r=${v.rid}`} className="enlace"><MapPin size={16} weight="bold" />Ver en el mapa</Link>
        </div>
      </div>
    </article>
  );
}

export default function Videos() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api("/videos?limite=30").then(setDatos).catch((e) => setError(e.message)); }, []);

  const destacado = datos?.videos?.[0];
  const resto = datos?.videos?.slice(1) || [];

  return (
    <>
    <PaginaHero foto="taganga" titulo="Videos de lo que pasa ahora" compacta
                texto="Clips que los vecinos graban y adjuntan a sus reportes: un arroyo crecido, un incendio en los cerros, una vía cerrada.">
      {datos && <Fuente fuente={datos._fuente} />}
    </PaginaHero>
    <div className="vid-seccion">
      {error && <p className="error" style={{ margin: "24px auto", maxWidth: 600 }}>{error}</p>}
      {!datos && !error && (
        <div className="vid-cargando">
          {[0, 1, 2].map((i) => <div key={i} className="esqueleto" style={{ aspectRatio: "16 / 9", borderRadius: 16 }} />)}
        </div>
      )}
      {datos?.total === 0 && (
        <div className="vid-vacio">
          <div className="icono-grande"><FilmStrip size={32} weight="bold" /></div>
          <h2>Todavía no hay videos</h2>
          <p>Cuando alguien adjunte un video a su reporte, aparecerá aquí.</p>
          <Link to="/reportar" className="boton atardecer"><Plus size={18} weight="bold" />Reportar con video</Link>
        </div>
      )}
      {destacado && (
        <div className="vid-contenido">
          <VideoDestacado v={destacado} />
          {resto.length > 0 && (
            <>
              <h2 className="vid-seccion-titulo">Más videos recientes</h2>
              <div className="vid-lista">
                {resto.map((v) => <VideoFila key={v.id} v={v} />)}
              </div>
            </>
          )}
        </div>
      )}
    </div>
    </>
  );
}
