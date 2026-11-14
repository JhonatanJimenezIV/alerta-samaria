import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MapContainer, Marker, TileLayer } from "react-leaflet";
import { api, qs } from "../api.js";
import { Buildings, ChartBar, CheckCircle, Lightbulb, Siren, Wrench } from "@phosphor-icons/react";
import { BARRIOS, ESTADOS, haceCuanto } from "../constantes.js";
import { IconoCategoria } from "../iconos.jsx";
import { Historial } from "../componentes/DetalleReporte.jsx";
import Galeria from "../componentes/Galeria.jsx";
import { CAPA_MAPA } from "../componentes/MapaReportes.jsx";
import { Estado, Fuente, Urgencia } from "../componentes/Insignias.jsx";
import { iconoReporte } from "../componentes/MapaReportes.jsx";
import TarjetaReporte from "../componentes/TarjetaReporte.jsx";
import { useSesion } from "../sesion.jsx";
import PaginaHero from "../componentes/PaginaHero.jsx";

const NOMBRES_CAT = { emergencias: "Emergencias", seguridad: "Seguridad", servicios: "Servicios públicos", vias: "Vías",
  transito: "Tránsito", ambiente: "Ambiente", animales: "Animales", playas: "Playas", otro: "Otro" };

function DetalleEntidad({ id, onCambio }) {
  const [r, setR] = useState(null);
  const [nota, setNota] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");

  const cargar = useCallback(() => {
    setError("");
    api(`/entidad/reportes/${id}`).then(setR).catch((e) => setError(e.message));
  }, [id]);
  useEffect(() => { setR(null); setMensaje(""); setNota(""); cargar(); }, [cargar]);

  const cambiar = async (estado) => {
    setMensaje("");
    try {
      await api(`/entidad/reportes/${id}/estado`, { metodo: "PATCH", body: { estado, nota } });
      setMensaje(`Reporte marcado como ${ESTADOS[estado].nombre.toLowerCase()}. Se invalidó su caché en Redis.`);
      setNota("");
      cargar();
      onCambio();
    } catch (e) {
      setMensaje(e.message);
    }
  };

  if (error) return <div className="caja"><p className="error">{error}</p></div>;
  if (!r) return <div className="caja"><p className="cargando">Cargando…</p></div>;
  return (
    <div className="caja detalle-entidad">
      <div className="detalle-cabecera">
        <span className="detalle-icono"><IconoCategoria categoria={r.categoria} size={24} /></span>
        <div><div className="detalle-categoria">{r.categoria_nombre}</div><h2>{r.subtipo_nombre}</h2></div>
      </div>
      <div className="tarjeta-insignias">
        <Urgencia nivel={r.urgencia} /> <Estado estado={r.estado} /> <Fuente fuente={r._fuente} />
        {r.confianza_reporte === "baja" && <span className="insignia u1">Confianza baja</span>}
      </div>
      {r.descripcion && <p className="detalle-desc">{r.descripcion}</p>}
      <Galeria media={r.media} />
      <dl className="detalle-datos">
        <dt>Dirección</dt><dd>{r.direccion || "—"}</dd>
        <dt>Referencia</dt><dd>{r.referencia || "—"}</dd>
        <dt>Barrio</dt><dd>{r.barrio} {r.comuna && `· ${r.comuna}`}</dd>
        <dt>Coordenadas exactas</dt><dd>{r.lat.toFixed(5)}, {r.lng.toFixed(5)}</dd>
        <dt>Confirmaciones</dt><dd>{r.confirmaciones}</dd>
        <dt>Contacto</dt>
        <dd>{r.contacto ? <>{r.contacto.nombre} · {r.contacto.telefono || "sin teléfono"} · {r.contacto.email}</>
                        : <span className="nota">El ciudadano no autorizó compartir su contacto</span>}</dd>
      </dl>
      <MapContainer center={[r.lat, r.lng]} zoom={17} className="mapa mini" key={r.id}>
        <TileLayer {...CAPA_MAPA} />
        <Marker position={[r.lat, r.lng]} icon={iconoReporte(r, true)} />
      </MapContainer>

      {r.estado !== "resuelto" && (
        <div className="acciones">
          <input placeholder="Nota para el ciudadano: cuadrilla asignada, tiempo estimado" value={nota} onChange={(e) => setNota(e.target.value)} />
          <div className="en-linea">
            {r.estado !== "en_atencion" && <button className="boton naranja" onClick={() => cambiar("en_atencion")}><Wrench size={18} weight="bold" />Tomar caso</button>}
            <button className="boton verde" onClick={() => cambiar("resuelto")}><CheckCircle size={18} weight="bold" />Marcar resuelto</button>
          </div>
        </div>
      )}
      {mensaje && <p className="nota destacada">{mensaje}</p>}

      <h3 className="subtitulo">Historial</h3>
      <Historial eventos={r.historial} />
    </div>
  );
}

function Estadisticas() {
  const hoy = new Date().toISOString().slice(0, 10);
  const [fecha, setFecha] = useState(hoy);
  const [stats, setStats] = useState(null);
  const [barrio, setBarrio] = useState("Bastidas");
  const [riesgo, setRiesgo] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { api(`/entidad/estadisticas${qs({ fecha })}`).then(setStats).catch((e) => setError(e.message)); }, [fecha]);
  useEffect(() => { api(`/entidad/riesgo/${encodeURIComponent(barrio)}`).then(setRiesgo).catch((e) => setError(e.message)); }, [barrio]);

  const maxB = stats ? Math.max(1, ...Object.values(stats.por_barrio)) : 1;
  const colorNivel = { alto: "#d92d20", medio: "#e67700", bajo: "#2f9e44" };
  return (
    <div className="dos-columnas">
      <div className="caja">
        <div className="lista-cabecera"><h2>Reportes del día</h2>
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} /></div>
        {error && <p className="error">{error}</p>}
        {stats && (
          <>
            <p className="cifra">{stats.total}<span> reportes</span></p>
            <h3>Por barrio</h3>
            {Object.entries(stats.por_barrio).map(([b, t]) => (
              <div key={b} className="ranking-fila"><span>{b}</span><span className="barra" style={{ width: `${(t / maxB) * 100}%` }} /><b>{t}</b></div>
            ))}
            <h3>Por categoría</h3>
            {Object.entries(stats.por_categoria).map(([c, t]) => (
              <div key={c} className="ranking-fila"><span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}><IconoCategoria categoria={c} size={16} />{NOMBRES_CAT[c] || c}</span><span className="barra" style={{ width: `${(t / stats.total) * 100}%` }} /><b>{t}</b></div>
            ))}
          </>
        )}
      </div>
      <div className="caja">
        <div className="lista-cabecera"><h2>Puntos de riesgo</h2>
          <select value={barrio} onChange={(e) => setBarrio(e.target.value)}>
            {BARRIOS.map((b) => <option key={b.nombre}>{b.nombre}</option>)}
          </select></div>
        <p className="nota">Cruza los reportes de inseguridad con los de alumbrado dañado en los últimos 30 días.</p>
        {riesgo && (
          <>
            <p className="cifra" style={{ color: colorNivel[riesgo.nivel] }}>{riesgo.nivel.toUpperCase()}<span> índice {riesgo.indice_riesgo}</span></p>
            <div className="ranking-fila"><span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}><Siren size={16} weight="bold" />Inseguridad</span><b>{riesgo.reportes_inseguridad}</b></div>
            <div className="ranking-fila"><span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}><Lightbulb size={16} weight="bold" />Alumbrado o sin luz</span><b>{riesgo.reportes_alumbrado}</b></div>
            {riesgo.hallazgo && <p className="nota destacada">{riesgo.hallazgo}</p>}
          </>
        )}
      </div>
    </div>
  );
}

export default function PanelEntidad() {
  const { usuario } = useSesion();
  const cats = usuario?.categorias_atendidas || [];
  const [vista, setVista] = useState("reportes");
  const [categoria, setCategoria] = useState(cats[0] || "");
  const [estado, setEstado] = useState("pendiente");
  const [datos, setDatos] = useState(null);
  const [sel, setSel] = useState(null);
  const [error, setError] = useState("");

  const cargar = useCallback(() => {
    if (!categoria) return;
    api(`/entidad/reportes${qs({ categoria, estado })}`).then((d) => { setDatos(d); setError(""); }).catch((e) => setError(e.message));
  }, [categoria, estado]);
  useEffect(() => { setSel(null); cargar(); }, [cargar]);

  if (!usuario) return <div className="pagina estrecha"><p><Link to="/ingresar">Ingresa</Link> con una cuenta de entidad.</p></div>;
  if (usuario.rol !== "entidad") return <div className="pagina estrecha"><p>Esta sección es solo para entidades.</p></div>;

  return (
    <>
    <PaginaHero foto="vistaSierra" compacta titulo={usuario.entidad || usuario.nombre}
                texto={`Atiende: ${cats.map((c) => NOMBRES_CAT[c] || c).join(", ").toLowerCase()}.`}>
      <div className="modo oscuro" style={{ maxWidth: 420, marginTop: 24 }}>
          <button className={vista === "reportes" ? "activo" : ""} onClick={() => setVista("reportes")}><Buildings size={18} weight="bold" />Reportes</button>
          <button className={vista === "stats" ? "activo" : ""} onClick={() => setVista("stats")}><ChartBar size={18} weight="bold" />Estadísticas y riesgo</button>
      </div>
    </PaginaHero>
    <div className="pagina panel-entidad superpuesta">

      {vista === "stats" ? <Estadisticas /> : (
        <>
          <div className="chips caja-chips">
            {cats.map((c) => (
              <button key={c} className={categoria === c ? "chip activo" : "chip"} onClick={() => setCategoria(c)}><IconoCategoria categoria={c} size={16} />{NOMBRES_CAT[c] || c}</button>
            ))}
            <span className="separador" />
            {Object.entries(ESTADOS).map(([k, v]) => (
              <button key={k} className={estado === k ? "chip activo" : "chip"} onClick={() => setEstado(k)}>{v.nombre}</button>
            ))}
          </div>
          {error && <p className="error">{error}</p>}
          <div className="entidad-cuerpo">
            <div className="lista">
              <p className="nota">{datos ? `${datos.total} reportes, los más urgentes primero` : "Cargando reportes…"}</p>
              {!datos && !error && [0, 1, 2].map((i) => <div key={i} className="esqueleto" style={{ height: 72, margin: "4px 0" }} />)}
              {datos?.reportes.map((r) => (
                <TarjetaReporte key={r.id} reporte={r} seleccionado={sel === r.id} onClick={() => setSel(r.id)} />
              ))}
              {datos?.total === 0 && <p className="vacio">No hay reportes en este estado.</p>}
            </div>
            {sel ? <DetalleEntidad id={sel} onCambio={cargar} /> : <div className="caja vacio">Selecciona un reporte para ver el detalle completo.</div>}
          </div>
        </>
      )}
    </div>
    </>
  );
}
