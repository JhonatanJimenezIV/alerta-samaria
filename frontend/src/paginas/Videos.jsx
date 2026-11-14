import { FilmStrip, Plus } from "@phosphor-icons/react";
import { Link } from "react-router-dom";

export default function Videos() {
  return (
    <div className="pagina estrecha">
      <div className="pagina-cabecera">
        <h1>Videos de lo que pasa ahora</h1>
        <p>Clips cortos que los vecinos graban y adjuntan a sus reportes: un arroyo crecido, un incendio en los cerros, una vía cerrada.</p>
      </div>
      <div className="caja estado-vacio">
        <div>
          <div className="icono-grande"><FilmStrip size={32} weight="bold" /></div>
          <h2>Todavía no hay videos</h2>
          <p>Los videos llegarán con la próxima versión, cuando los reportes permitan adjuntar fotos y clips. Mientras tanto, puedes reportar lo que ves.</p>
          <Link to="/reportar" className="boton reportar"><Plus size={18} weight="bold" />Reportar algo</Link>
        </div>
      </div>
    </div>
  );
}
