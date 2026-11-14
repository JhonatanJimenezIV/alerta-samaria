import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import TarjetaReporte from "../componentes/TarjetaReporte.jsx";
import { useSesion } from "../sesion.jsx";

export default function MisReportes() {
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const [reportes, setReportes] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (usuario) api(`/usuarios/${usuario.id}/reportes?limite=50`).then((d) => setReportes(d.reportes)).catch((e) => setError(e.message));
  }, [usuario]);

  if (!usuario) return <div className="pagina estrecha"><p><Link to="/ingresar">Ingresa</Link> para ver tus reportes.</p></div>;

  return (
    <div className="pagina estrecha">
      <div className="pagina-cabecera"><h1>Mis reportes</h1><p>Todo lo que has reportado, del más reciente al más antiguo.</p></div>
      {error && <p className="error">{error}</p>}
      {reportes?.length === 0 && <p className="vacio">Aún no has hecho reportes. <Link to="/reportar">Crea el primero</Link>.</p>}
      <div className="lista">
        {reportes?.map((r) => (
          <TarjetaReporte key={r.id} reporte={r} onClick={() => navegar(`/mapa?r=${r.id}`)}
                          extra={r.anonimo && <span className="insignia estado">Anónimo</span>} />
        ))}
      </div>
    </div>
  );
}
