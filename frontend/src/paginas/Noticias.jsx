import { ArrowSquareOut, Newspaper, Plus } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { haceCuanto } from "../constantes.js";
import { Fuente } from "../componentes/Insignias.jsx";
import { useSesion } from "../sesion.jsx";

// Noticias de Santa Marta Al Día. Cada publicación se muestra con el plugin oficial de Facebook
// (video.php para videos y reels, post.php para publicaciones): se ve y se reproduce aquí mismo.
// En la base de datos solo se guarda el enlace; el contenido sigue siendo del medio.
const PAGINA = "https://www.facebook.com/SantaMartaAD";
const ANCHO = 420;

function Publicacion({ n }) {
  const esVideo = n.clase === "video";
  const esReel = n.url.includes("/reel/");
  const plugin = esVideo ? "video" : "post";
  const src = `https://www.facebook.com/plugins/${plugin}.php?${new URLSearchParams({ href: n.url, show_text: "true", width: String(ANCHO) })}`;
  return (
    <article className="noticia">
      <header className="noticia-cab">
        <span className="noticia-medio">SM</span>
        <div>
          <b>{n.fuente || "Santa Marta Al Día"}</b>
          <span className="nota">{esVideo ? (esReel ? "Reel" : "Video") : "Publicación"}, agregada {haceCuanto(n.creado_en)}</span>
        </div>
        <a href={n.url} target="_blank" rel="noreferrer" className="enlace" aria-label="Abrir en Facebook"><ArrowSquareOut size={18} weight="bold" /></a>
      </header>
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
    <form className="caja" onSubmit={enviar}>
      <h2>Agregar una publicación</h2>
      <p className="nota">Pega el enlace de una publicación, video o reel de la página de Facebook del medio.</p>
      <div className="en-linea" style={{ marginTop: 12 }}>
        <input required placeholder="https://www.facebook.com/reel/..." value={url} onChange={(e) => setUrl(e.target.value)} />
        <button className="boton primario"><Plus size={18} weight="bold" />Agregar</button>
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
    <div className="pagina noticias-pagina">
      <div className="noticias-columna">
        <div className="pagina-cabecera lista-cabecera" style={{ padding: 0, alignItems: "flex-end" }}>
          <div>
            <h1>Noticias de Santa Marta</h1>
            <p>Lo último de Santa Marta Al Día. Los videos se reproducen aquí mismo; el contenido es de ese medio.</p>
          </div>
          {datos && <Fuente fuente={datos._fuente} />}
        </div>
        {error && <p className="error">{error}</p>}
        {!datos && !error && [0, 1].map((i) => <div key={i} className="esqueleto" style={{ height: 520, maxWidth: ANCHO, margin: "0 auto 16px" }} />)}
        {datos?.total === 0 && (
          <div className="caja estado-vacio">
            <div>
              <div className="icono-grande"><Newspaper size={32} weight="bold" /></div>
              <h2>Todavía no hay noticias</h2>
              <p>Corre <code>python scripts/seed.py</code> o agrega una publicación desde una cuenta de entidad.</p>
            </div>
          </div>
        )}
        <div className="noticias-lista">
          {datos?.noticias.map((n) => <Publicacion key={n.id} n={n} />)}
        </div>
      </div>
      <aside className="noticias-lado">
        {usuario?.rol === "entidad" && <Agregar alAgregar={cargar} />}
        <div className="caja">
          <h2>Santa Marta Al Día</h2>
          <p className="nota">Medio de comunicación web de Santa Marta. Las publicaciones se muestran con los plugins oficiales de Facebook.</p>
          <a href={PAGINA} target="_blank" rel="noreferrer" className="boton" style={{ marginTop: 12 }}><ArrowSquareOut size={18} weight="bold" />Ver la página completa</a>
        </div>
      </aside>
    </div>
  );
}
