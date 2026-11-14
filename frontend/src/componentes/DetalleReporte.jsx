import { Eye, Phone, X } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { ESTADOS, NOMBRES_CATEGORIA, haceCuanto } from "../constantes.js";
import { IconoCategoria } from "../iconos.jsx";
import { useSesion } from "../sesion.jsx";
import { Estado, Fuente, Urgencia } from "./Insignias.jsx";

export function Historial({ eventos }) {
  return (
    <ol className="historial">
      {eventos?.map((h, i) => (
        <li key={i}>
          <span className="punto" style={{ background: ESTADOS[h.estado_nuevo]?.color }} />
          <div>
            <b>{ESTADOS[h.estado_nuevo]?.nombre || h.estado_nuevo}</b>, {haceCuanto(h.fecha)}
            {h.nota && <div className="nota">{h.nota}</div>}
          </div>
        </li>
      ))}
    </ol>
  );
}

function Esqueleto() {
  return (
    <div aria-label="Cargando reporte">
      <div className="esqueleto" style={{ height: 48, width: "70%", marginBottom: 16 }} />
      <div className="esqueleto" style={{ height: 24, width: "45%", marginBottom: 24 }} />
      <div className="esqueleto" style={{ height: 96, marginBottom: 16 }} />
      <div className="esqueleto" style={{ height: 120 }} />
    </div>
  );
}

export default function DetalleReporte({ id, onCerrar, onCambio }) {
  const { usuario } = useSesion();
  const [r, setR] = useState(null);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [enviando, setEnviando] = useState(false);

  const cargar = () => {
    setError("");
    api(`/reportes/${id}`).then(setR).catch((e) => setError(e.message));
  };
  useEffect(() => { setR(null); setMensaje(""); cargar(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const confirmar = async () => {
    setEnviando(true);
    setMensaje("");
    try {
      const res = await api(`/reportes/${id}/confirmaciones`, { metodo: "POST" });
      setMensaje(res.estado === "confirmado" && r.estado === "pendiente"
        ? "Confirmación registrada. El reporte pasó a confirmado."
        : "Confirmación registrada.");
      cargar();
      onCambio?.();
    } catch (e) {
      setMensaje(e.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <aside className="detalle" aria-label="Detalle del reporte">
      <button className="cerrar" onClick={onCerrar} aria-label="Cerrar detalle"><X size={18} weight="bold" /></button>
      {error && <p className="error">{error}</p>}
      {!r && !error && <Esqueleto />}
      {r && (
        <>
          <div className="detalle-cabecera">
            <span className="detalle-icono"><IconoCategoria categoria={r.categoria} size={24} /></span>
            <div>
              <div className="detalle-categoria">{r.categoria_nombre}</div>
              <h2>{r.subtipo_nombre}</h2>
            </div>
          </div>
          <div className="tarjeta-insignias">
            <Urgencia nivel={r.urgencia} /> <Estado estado={r.estado} /> <Fuente fuente={r._fuente} />
          </div>
          {r.aviso_123 && r.estado !== "resuelto" && (
            <div className="aviso-123"><Phone size={18} weight="bold" />Si hay riesgo para la vida, llama al 123</div>
          )}
          {r.descripcion && <p className="detalle-desc">{r.descripcion}</p>}
          <dl className="detalle-datos">
            <dt>Barrio</dt><dd>{r.barrio}{r.comuna && `, ${r.comuna}`}</dd>
            {r.direccion && (<><dt>Dirección</dt><dd>{r.direccion}</dd></>)}
            {r.referencia && (<><dt>Referencia</dt><dd>{r.referencia}</dd></>)}
            {r.ubicacion_aproximada && (<><dt>Ubicación</dt><dd>Aproximada, a unos 150 m, para proteger a quien reporta</dd></>)}
            {r.tambien_afecta?.length > 0 && (<><dt>También afecta</dt><dd>{r.tambien_afecta.map((a) => NOMBRES_CATEGORIA[a] || a).join(", ")}</dd></>)}
            <dt>Reportado por</dt><dd>{r.autor}, {haceCuanto(r.creado_en)}</dd>
            <dt>Confirmaciones</dt><dd>{r.confirmaciones}</dd>
          </dl>

          {usuario?.rol === "ciudadano" && r.estado !== "resuelto" && (
            <button className="boton primario ancho" onClick={confirmar} disabled={enviando}>
              <Eye size={20} weight="bold" />{enviando ? "Registrando…" : "Yo también lo veo"}
            </button>
          )}
          {!usuario && <p className="nota"><Link to="/ingresar">Ingresa</Link> para confirmar este reporte.</p>}
          {mensaje && <p className="nota destacada">{mensaje}</p>}

          <h3 className="subtitulo">Historial</h3>
          <Historial eventos={r.historial} />
        </>
      )}
    </aside>
  );
}
