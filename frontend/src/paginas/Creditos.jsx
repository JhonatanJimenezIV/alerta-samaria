import { FOTOS, paginaFoto, urlFoto } from "../fotos.js";

export default function Creditos() {
  return (
    <div className="pagina">
      <div className="pagina-cabecera">
        <h1>Créditos de las fotografías</h1>
        <p>Todas las fotos de Santa Marta vienen de Wikimedia Commons y se usan bajo sus licencias Creative Commons. En la web se muestran con más saturación y contraste.</p>
      </div>
      <div className="creditos">
        {Object.keys(FOTOS).map((k) => (
          <figure key={k}>
            <img src={urlFoto(k, 640)} alt={FOTOS[k].lugar} loading="lazy" />
            <figcaption>
              <b>{FOTOS[k].lugar}</b><br />
              Foto de {FOTOS[k].autor}, {FOTOS[k].licencia}.{" "}
              <a href={paginaFoto(k)} target="_blank" rel="noreferrer">Ver en Wikimedia Commons</a>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}
