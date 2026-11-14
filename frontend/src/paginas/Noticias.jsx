import { FacebookLogo, Newspaper } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";

// Página de Facebook de Santa Marta Al Día (medio local), se puede cambiar con VITE_FACEBOOK_PAGE. Se incrusta con el plugin oficial de Facebook (Page Plugin):
// se actualiza solo y no copiamos ni almacenamos su contenido.
const PAGINA_FACEBOOK = import.meta.env.VITE_FACEBOOK_PAGE || "https://www.facebook.com/SantaMartaAD";

export default function Noticias() {
  const contenedor = useRef(null);
  const [ancho, setAncho] = useState(500);
  useEffect(() => {
    const medir = () => setAncho(Math.min(500, Math.max(280, (contenedor.current?.clientWidth || 500) - 32)));
    medir();
    window.addEventListener("resize", medir);
    return () => window.removeEventListener("resize", medir);
  }, []);

  const src = PAGINA_FACEBOOK && `https://www.facebook.com/plugins/page.php?${new URLSearchParams({
    href: PAGINA_FACEBOOK, tabs: "timeline,videos", width: String(ancho), height: "900",
    small_header: "false", adapt_container_width: "true", hide_cover: "false", show_facepile: "false",
  })}`;

  return (
    <div className="pagina estrecha" ref={contenedor}>
      <div className="pagina-cabecera">
        <h1>Noticias de Santa Marta</h1>
        <p>Las publicaciones más recientes de Santa Marta Al Día, un medio local, directamente desde su página de Facebook. El contenido es de ese medio.</p>
      </div>
      {src ? (
        <div className="fb-marco">
          <iframe title="Noticias desde Facebook" src={src} width={ancho} height="900" style={{ border: 0, overflow: "hidden" }}
                  allow="encrypted-media; picture-in-picture; web-share" loading="lazy" />
        </div>
      ) : (
        <div className="caja estado-vacio">
          <div>
            <div className="icono-grande"><Newspaper size={32} weight="bold" /></div>
            <h2>Falta conectar la página de noticias</h2>
            <p>Agrega la dirección de la página de Facebook del medio en <code>frontend/.env.local</code> como
              <code>VITE_FACEBOOK_PAGE</code> y reinicia <code>npm run dev</code>.</p>
            <p className="nota" style={{ display: "inline-flex", gap: 6, alignItems: "center" }}><FacebookLogo size={18} weight="bold" />Se muestra con el plugin oficial de Facebook.</p>
          </div>
        </div>
      )}
    </div>
  );
}
