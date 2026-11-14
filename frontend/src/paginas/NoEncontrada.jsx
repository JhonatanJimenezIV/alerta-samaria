import { MapTrifold } from "@phosphor-icons/react";
import { Link } from "react-router-dom";

export default function NoEncontrada() {
  return (
    <div className="pagina estrecha">
      <div className="caja estado-vacio">
        <div>
          <div className="icono-grande"><MapTrifold size={32} weight="bold" /></div>
          <h2>Esta página no existe</h2>
          <p>Puede que el enlace esté mal escrito o que la página se haya movido.</p>
          <Link to="/mapa" className="boton primario">Ir al mapa en vivo</Link>
        </div>
      </div>
    </div>
  );
}
