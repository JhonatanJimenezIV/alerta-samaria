import { FOTOS, urlFoto } from "../fotos.js";

// Portada de sección con una foto real de la ciudad, en la misma línea visual de la página de inicio.
export default function PaginaHero({ foto, titulo, texto, children, compacta = false, pantalla = false }) {
  return (
    <section className={`pagina-hero ${compacta ? "compacta" : ""} ${pantalla ? "pantalla" : ""}`}>
      <img src={urlFoto(foto, 1920)} alt="" className="pagina-hero-foto" />
      <div className="pagina-hero-velo" aria-hidden="true" />
      <div className="pagina-hero-contenido">
        <h1>{titulo}</h1>
        {texto && <p>{texto}</p>}
        {children}
      </div>
      <span className="pagina-hero-credito">{FOTOS[foto].lugar}. Foto: {FOTOS[foto].autor}, {FOTOS[foto].licencia}</span>
    </section>
  );
}
