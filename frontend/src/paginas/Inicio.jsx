import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, qs } from "../api.js";
import { Crosshair, Clock, Trophy } from "@phosphor-icons/react";
import { CENTRO_SANTA_MARTA } from "../constantes.js";
import { IconoCategoria } from "../iconos.jsx";
import DetalleReporte from "../componentes/DetalleReporte.jsx";
import { Fuente } from "../componentes/Insignias.jsx";
import MapaReportes from "../componentes/MapaReportes.jsx";
import TarjetaReporte from "../componentes/TarjetaReporte.jsx";

const REFRESCO_MS = 15000;

export default function Inicio() {
  const [params, setParams] = useSearchParams();
  const [categorias, setCategorias] = useState([]);
  const [categoria, setCategoria] = useState("");
  const [modo, setModo] = useState("feed"); // feed | cerca
  const [centro, setCentro] = useState(null);
  const [km, setKm] = useState(1);
  const [datos, setDatos] = useState({ reportes: [], _fuente: null });
  const [ranking, setRanking] = useState(null);
  const [error, setError] = useState("");
  const [cargado, setCargado] = useState(false);
  const [enfocar, setEnfocar] = useState(null);
  const seleccionado = params.get("r");

  const seleccionar = (id) => {
    const r = datos.reportes.find((x) => x.id === id);
    if (r) setEnfocar([r.lat, r.lng]);
    setParams(id ? { r: id } : {});
  };

  const cargar = useCallback(async () => {
    try {
      const d = modo === "cerca" && centro
        ? await api(`/reportes/cerca${qs({ lat: centro[0], lng: centro[1], km })}`)
        : await api(`/reportes/feed${qs({ categoria, limite: 100 })}`);
      if (modo === "cerca" && categoria) {
        d.reportes = d.reportes.filter((r) => r.categoria === categoria || r.tambien_afecta?.includes(categoria));
      }
      setDatos(d);
      setCargado(true);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, [modo, centro, km, categoria]);

  useEffect(() => {
    api("/categorias").then((d) => setCategorias(d.categorias)).catch(() => {});
    api("/ranking/barrios").then(setRanking).catch(() => {});
  }, []);

  // Feed "en vivo": se refresca cada 15 s
  useEffect(() => {
    cargar();
    const t = setInterval(cargar, REFRESCO_MS);
    return () => clearInterval(t);
  }, [cargar]);

  const activarCerca = () => {
    setModo("cerca");
    if (!navigator.geolocation) { setCentro(CENTRO_SANTA_MARTA); return; }
    navigator.geolocation.getCurrentPosition(
      (p) => { const c = [p.coords.latitude, p.coords.longitude]; setCentro(c); setEnfocar(c); },
      () => { setCentro(CENTRO_SANTA_MARTA); setEnfocar(CENTRO_SANTA_MARTA); },
      { timeout: 5000 }
    );
  };

  return (
    <div className="inicio">
      <section className="panel-lateral">
        <div className="filtros">
          <div className="modo">
            <button className={modo === "feed" ? "activo" : ""} onClick={() => setModo("feed")}><Clock size={18} weight="bold" />En vivo</button>
            <button className={modo === "cerca" ? "activo" : ""} onClick={activarCerca}><Crosshair size={18} weight="bold" />Cerca de mí</button>
          </div>
          {modo === "cerca" && (
            <div className="radio">
              Radio: <b>{km} km</b>
              <input type="range" min="0.5" max="10" step="0.5" value={km} onChange={(e) => setKm(Number(e.target.value))} />
              <span className="nota">Toca el mapa para buscar en otro punto</span>
            </div>
          )}
          <div className="chips">
            <button className={!categoria ? "chip activo" : "chip"} onClick={() => setCategoria("")}>Todas</button>
            {categorias.map((c) => (
              <button key={c.id} className={categoria === c.id ? "chip activo" : "chip"} onClick={() => setCategoria(c.id)}>
                <IconoCategoria categoria={c.id} size={16} /> {c.nombre}
              </button>
            ))}
          </div>
        </div>

        <div className="lista-cabecera">
          <span><b>{datos.reportes.length}</b> incidentes activos</span>
          <Fuente fuente={datos._fuente} />
        </div>
        {error && <p className="error">{error}</p>}
        <div className="lista">
          {datos.reportes.map((r) => (
            <TarjetaReporte key={r.id} reporte={r} seleccionado={r.id === seleccionado} onClick={() => seleccionar(r.id)} />
          ))}
          {!error && cargado && datos.reportes.length === 0 && <p className="vacio">No hay incidentes activos con este filtro.</p>}
          {!cargado && !error && [0, 1, 2, 3].map((i) => <div key={i} className="esqueleto" style={{ height: 76, margin: "4px 0" }} />)}
        </div>

        {ranking?.ranking?.length > 0 && (
          <div className="ranking">
            <div className="lista-cabecera">
              <b style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><Trophy size={18} weight="bold" />Barrios con más reportes esta semana</b>
              <Fuente fuente={ranking._fuente} />
            </div>
            {ranking.ranking.slice(0, 5).map((b, i) => (
              <div key={b.barrio} className="ranking-fila">
                <span>{i + 1}. {b.barrio}</span>
                <span className="barra" style={{ width: `${(b.total / ranking.ranking[0].total) * 100}%` }} />
                <b>{b.total}</b>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="zona-mapa">
        <MapaReportes
          reportes={datos.reportes}
          seleccionado={seleccionado}
          onSeleccionar={seleccionar}
          enfocar={enfocar}
          circulo={modo === "cerca" && centro ? { centro, km } : null}
          onClicMapa={modo === "cerca" ? (p) => setCentro(p) : undefined}
        />
        {seleccionado && (
          <DetalleReporte id={seleccionado} onCerrar={() => setParams({})} onCambio={cargar} />
        )}
      </section>
    </div>
  );
}
