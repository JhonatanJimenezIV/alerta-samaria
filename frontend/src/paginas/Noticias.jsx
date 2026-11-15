import { ArrowSquareOut, Newspaper, Plus, FacebookLogo, Globe } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { haceCuanto } from "../constantes.js";
import { Fuente } from "../componentes/Insignias.jsx";
import { useSesion } from "../sesion.jsx";
import PaginaHero from "../componentes/PaginaHero.jsx";

const PAGINA = "https://www.facebook.com/SantaMartaAD";
const ANCHO = 420;

function Publicacion({ n }) {
  const esVideo = n.clase === "video";
  const esReel = n.url.includes("/reel/");
  const plugin = esVideo ? "video" : "post";
  const src = `https://www.facebook.com/plugins/${plugin}.php?${new URLSearchParams({ href: n.url, show_text: "true", width: String(ANCHO) })}`;
  return (
    <article className="not-tarjeta">
      <div className="not-embed">
        <iframe
          title={`Publicación de ${n.fuente || "Santa Marta Al Día"}`}
          src={src}
          width={ANCHO}
          height={esReel ? 900 : esVideo ? 520 : 640}
          loading="lazy"
          style={{ border: 0, overflow: "hidden", maxWidth: "100%" }}
          scrolling="no"
          allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
          allowFullScreen
        />
      </div>
      <div className="not-lado">
        <div className="not-cab">
          <span className="not-medio-icono"><FacebookLogo size={20} weight="fill" /></span>
          <div>
            <b>{n.fuente || "Santa Marta Al Día"}</b>
            <span className="not-tipo">{esVideo ? (esReel ? "Reel" : "Video") : "Publicación"}</span>
          </div>
        </div>
        <p className="not-fecha">Agregada {haceCuanto(n.creado_en)}</p>
        <div className="not-comentarios">
          <h4>Sobre esta publicación</h4>
          <p>Esta noticia proviene de <strong>Santa Marta Al Día</strong>, medio de comunicación web de Santa Marta. El contenido y los comentarios se muestran con los plugins oficiales de Facebook.</p>
          <p>Puedes interactuar con la publicación directamente: darle me gusta, comentar o compartirla desde aquí.</p>
        </div>
        <a href={n.url} target="_blank" rel="noreferrer" className="boton pequeno not-btn-fb">
          <ArrowSquareOut size={16} weight="bold" />Abrir en Facebook
        </a>
      </div>
    </article>
  );
}

function Agregar({ alAgregar }) {
  const [url, setUrl] = useState("");
  const [estado, setEstado] = useState("");
  const enviar = async (e) => {
    e.preventDefault();
    setEstado("");
    try {
      await api("/noticias", { metodo: "POST", body: { url } });
      setUrl("");
      setEstado("Publicación agregada.");
      alAgregar();
    } catch (err) {
      setEstado(err.message);
    }
  };
  return (
    <form className="not-agregar" onSubmit={enviar}>
      <h3>Agregar una publicación</h3>
      <p>Pega el enlace de una publicación, video o reel de la página de Facebook del medio.</p>
      <div className="en-linea" style={{ marginTop: 12 }}>
        <input required placeholder="https://www.facebook.com/reel/..." value={url} onChange={(e) => setUrl(e.target.value)} />
        <button className="boton primario pequeno"><Plus size={16} weight="bold" />Agregar</button>
      </div>
      {estado && <p className="nota destacada" style={{ marginTop: 12 }}>{estado}</p>}
    </form>
  );
}

export default function Noticias() {
  const { usuario } = useSesion();
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  const cargar = () => api("/noticias").then(setDatos).catch((e) => setError(e.message));
  useEffect(() => { cargar(); }, []);

  return (
    <>
    <PaginaHero foto="catedral" titulo="Noticias de Santa Marta" compacta
                texto="Lo último de Santa Marta Al Día. Los videos y publicaciones se reproducen aquí mismo.">
      {datos && <Fuente fuente={datos._fuente} />}
    </PaginaHero>
    <div className="not-seccion">
      {/* Barra lateral fija */}
      <aside className="not-sidebar">
        <div className="not-sidebar-card">
          <div className="not-sidebar-medio">
            <span className="not-medio-grande"><Globe size={28} weight="bold" /></span>
            <div>
              <h3>Santa Marta Al Día</h3>
              <p>Medio de comunicación web de Santa Marta</p>
            </div>
          </div>
          <p className="not-sidebar-desc">Las publicaciones se muestran con los plugins oficiales de Facebook. El contenido es de ese medio.</p>
          <a href={PAGINA} target="_blank" rel="noreferrer" className="boton primario pequeno not-sidebar-btn">
            <ArrowSquareOut size={16} weight="bold" />Ver la página completa
          </a>
        </div>
        {usuario?.rol === "entidad" && <Agregar alAgregar={cargar} />}
      </aside>

      {/* Feed de noticias */}
      <div className="not-feed">
        {error && <p className="error">{error}</p>}
        {!datos && !error && [0, 1].map((i) => <div key={i} className="esqueleto" style={{ height: 480, borderRadius: 16 }} />)}
        {datos?.total === 0 && (
          <div className="not-vacio">
            <div className="icono-grande"><Newspaper size={32} weight="bold" /></div>
            <h2>Todavía no hay noticias</h2>
            <p>Corre <code>python scripts/seed.py</code> o agrega una publicación desde una cuenta de entidad.</p>
          </div>
        )}
        {datos?.noticias.map((n) => <Publicacion key={n.id} n={n} />)}
      </div>
    </div>
    </>
  );
}
