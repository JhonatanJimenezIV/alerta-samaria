import L from "leaflet";
import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { Link, useNavigate } from "react-router-dom";
import { adjuntarArchivo, api } from "../api.js";
import { Camera, Crosshair, LockKey, MapPin, Phone, Trash, VideoCamera } from "@phosphor-icons/react";
import { renderToStaticMarkup } from "react-dom/server";
import { BARRIOS, CENTRO_SANTA_MARTA, NOMBRES_CATEGORIA, URGENCIA, barrioMasCercano } from "../constantes.js";
import { CAPA_MAPA } from "../componentes/MapaReportes.jsx";
import { useSesion } from "../sesion.jsx";
import PaginaHero from "../componentes/PaginaHero.jsx";

const iconoPin = L.divIcon({
  className: "",
  html: `<div class="pin-reporte">${renderToStaticMarkup(<MapPin size={44} weight="fill" color="#E8553A" />)}</div>`,
  iconSize: [44, 44],
  iconAnchor: [22, 42],
});

function Selector({ posicion, onCambio }) {
  useMapEvents({ click: (e) => onCambio([e.latlng.lat, e.latlng.lng]) });
  const ref = useRef(null);
  return (
    <Marker position={posicion} icon={iconoPin} draggable ref={ref}
            eventHandlers={{ dragend: () => { const p = ref.current.getLatLng(); onCambio([p.lat, p.lng]); } }} />
  );
}

function Recentrar({ punto }) {
  const mapa = useMap();
  useEffect(() => { if (punto) mapa.setView(punto, 17); }, [punto, mapa]);
  return null;
}

// Geocodificación inversa con Nominatim (OpenStreetMap). Si falla, el usuario escribe la dirección.
async function direccionDe([lat, lng]) {
  try {
    const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&accept-language=es`);
    const d = await r.json();
    const a = d.address || {};
    return [a.road, a.house_number].filter(Boolean).join(" ") || "";
  } catch {
    return "";
  }
}

export default function Reportar() {
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const [categorias, setCategorias] = useState([]);
  const [form, setForm] = useState({ categoria: "", subtipo: "", descripcion: "", direccion: "", referencia: "",
                                     barrio: "", comuna: "", anonimo: false, contacto_autorizado: false });
  const [posicion, setPosicion] = useState(CENTRO_SANTA_MARTA);
  const [gps, setGps] = useState(null);
  const [centrar, setCentrar] = useState(null);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [archivos, setArchivos] = useState([]);
  const [progreso, setProgreso] = useState("");

  useEffect(() => {
    api("/categorias").then((d) => setCategorias(d.categorias)).catch((e) => setError(e.message));
    navigator.geolocation?.getCurrentPosition(
      (p) => { const c = [p.coords.latitude, p.coords.longitude]; setGps(c); moverPin(c); setCentrar(c); },
      () => moverPin(CENTRO_SANTA_MARTA),
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const moverPin = async (p) => {
    setPosicion(p);
    const b = barrioMasCercano(p[0], p[1]);
    setForm((f) => ({ ...f, barrio: b.nombre, comuna: b.comuna }));
    const dir = await direccionDe(p);
    if (dir) setForm((f) => ({ ...f, direccion: dir }));
  };

  const cat = categorias.find((c) => c.id === form.categoria);
  const sub = cat?.subtipos.find((s) => s.id === form.subtipo);
  const campo = (k) => ({ value: form[k], onChange: (e) => setForm({ ...form, [k]: e.target.value }) });
  const barrios = useMemo(() => BARRIOS.map((b) => b.nombre), []);

  if (!usuario || usuario.rol !== "ciudadano") {
    return (
      <PaginaHero foto="obras" pantalla titulo="Reporta lo que está pasando"
                  texto={usuario ? "Las cuentas de entidad atienden reportes pero no los crean. Entra con una cuenta de ciudadano para reportar."
                                 : "Para reportar necesitas una cuenta: así cada reporte tiene a un vecino verificado detrás. Ver el mapa no la requiere."}>
        <div className="en-linea" style={{ marginTop: 24, flexWrap: "wrap" }}>
          <Link to="/ingresar" className="boton atardecer"><MapPin size={18} weight="bold" />{usuario ? "Cambiar de cuenta" : "Ingresar o crear cuenta"}</Link>
          <Link to="/mapa" className="boton boton-cristal">Ver el mapa en vivo</Link>
        </div>
      </PaginaHero>
    );
  }

  const enviar = async (e) => {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      setProgreso("Publicando el reporte");
      const r = await api("/reportes", {
        metodo: "POST",
        body: { ...form, lat: posicion[0], lng: posicion[1], ubic_reportante: gps ? { lat: gps[0], lng: gps[1] } : undefined },
      });
      // Los adjuntos se suben después de crear el reporte, uno por uno, directo a S3
      const fallidos = [];
      for (const [i, a] of archivos.entries()) {
        try {
          await adjuntarArchivo(r.id, a, (pct) => setProgreso(`Subiendo ${i + 1} de ${archivos.length}: ${pct} %`));
        } catch (err) {
          fallidos.push(`${a.name}: ${err.message}`);
        }
      }
      if (fallidos.length) {
        setError(`El reporte se publicó, pero no se pudieron subir estos archivos. ${fallidos.join(". ")}`);
        setTimeout(() => navegar(`/mapa?r=${r.id}`), 4000);
        return;
      }
      navegar(`/mapa?r=${r.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
      setProgreso("");
    }
  };

  const LIMITES = { foto: 8, video: 50 };
  const agregarArchivos = (lista) => {
    const nuevos = [...archivos];
    for (const a of lista) {
      const clase = a.type.startsWith("video/") ? "video" : a.type.startsWith("image/") ? "foto" : null;
      if (!clase) { setError(`${a.name} no es una foto ni un video`); continue; }
      if (a.size > LIMITES[clase] * 1024 * 1024) { setError(`${a.name} supera el máximo de ${LIMITES[clase]} MB para un ${clase}`); continue; }
      if (nuevos.length >= 4) { setError("Puedes adjuntar máximo 4 fotos o videos"); break; }
      nuevos.push(a);
    }
    setArchivos(nuevos);
  };

  return (
    <>
    <PaginaHero foto="obras" compacta titulo="Reporta lo que está pasando"
                texto="Tu reporte aparece en el mapa al instante y le llega a la entidad que lo tiene que resolver." />
    <div className="pagina reportar superpuesta">
      <form className="caja" onSubmit={enviar}>
        <h2 className="heading-5" style={{ marginBottom: 16 }}>Qué viste y dónde</h2>
        {error && <p className="error">{error}</p>}

        <label>Categoría
          <select required {...campo("categoria")} onChange={(e) => setForm({ ...form, categoria: e.target.value, subtipo: "" })}>
            <option value="">Selecciona…</option>
            {categorias.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>
        </label>
        {cat && (
          <label>¿Qué está pasando?
            <select required {...campo("subtipo")}>
              <option value="">Selecciona…</option>
              {cat.subtipos.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}
            </select>
          </label>
        )}
        {sub && (
          <p className="nota">
            Urgencia <b style={{ color: URGENCIA[sub.urgencia].color }}>{URGENCIA[sub.urgencia].nombre.toLowerCase()}</b>.
            Se verá en el mapa durante {sub.horas >= 48 ? `${Math.round(sub.horas / 24)} días` : `${sub.horas} horas`}.
            {sub.tambien_afecta.length > 0 && <> También afecta a {sub.tambien_afecta.map((a) => NOMBRES_CATEGORIA[a]).join(" y ").toLowerCase()}.</>}
          </p>
        )}
        {cat?.aviso_123 && <div className="aviso-123"><Phone size={18} weight="bold" />Si hay riesgo para la vida, llama primero al 123</div>}
        {cat?.ubicacion_aproximada && (
          <p className="nota destacada" style={{ display: "flex", gap: 8 }}><LockKey size={20} weight="bold" style={{ flex: "none" }} /><span>En Seguridad el mapa público muestra una ubicación aproximada (~150 m) y no se
            publica tu nombre. No incluyas nombres ni descripciones físicas de personas.</span></p>
        )}

        <label>Descripción
          <textarea rows={3} maxLength={1000} placeholder="Describe lo que ves" {...campo("descripcion")} />
        </label>
        <div className="dos-columnas">
          <label>Barrio
            <select required {...campo("barrio")}
                    onChange={(e) => { const b = BARRIOS.find((x) => x.nombre === e.target.value); setForm({ ...form, barrio: b.nombre, comuna: b.comuna }); }}>
              {barrios.map((b) => <option key={b}>{b}</option>)}
            </select>
          </label>
          <label>Dirección<input placeholder="Cra 4 #22-10" {...campo("direccion")} /></label>
        </div>
        <label>Punto de referencia<input placeholder="Frente a la tienda…" {...campo("referencia")} /></label>

        {form.categoria && form.categoria !== "seguridad" && (
          <div className="adjuntos">
            <span className="adjuntos-titulo">Fotos o videos <span className="nota">(opcional, máximo 4; fotos hasta 8 MB, videos hasta 50 MB)</span></span>
            <label className="adjuntos-boton">
              <input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime" multiple
                     onChange={(e) => { agregarArchivos([...e.target.files]); e.target.value = ""; }} />
              <Camera size={20} weight="bold" />Agregar foto o video
            </label>
            {archivos.length > 0 && (
              <ul className="adjuntos-lista">
                {archivos.map((a, i) => (
                  <li key={`${a.name}-${i}`}>
                    {a.type.startsWith("video/") ? <VideoCamera size={18} weight="bold" /> : <Camera size={18} weight="bold" />}
                    <span>{a.name}</span>
                    <span className="nota">{(a.size / 1024 / 1024).toFixed(1)} MB</span>
                    <button type="button" className="enlace" aria-label={`Quitar ${a.name}`} onClick={() => setArchivos(archivos.filter((_, j) => j !== i))}><Trash size={18} weight="bold" /></button>
                  </li>
                ))}
              </ul>
            )}
            <p className="nota">Evita que se vean rostros o placas de vehículos.</p>
          </div>
        )}
        {form.categoria === "seguridad" && <p className="nota">En Seguridad no se permiten fotos ni videos, para proteger a las personas involucradas.</p>}

        <label className="check"><input type="checkbox" checked={form.anonimo}
               onChange={(e) => setForm({ ...form, anonimo: e.target.checked })} /> Publicar como anónimo</label>
        <label className="check"><input type="checkbox" checked={form.contacto_autorizado}
               onChange={(e) => setForm({ ...form, contacto_autorizado: e.target.checked })} />
          Autorizo que la entidad responsable me contacte sobre este reporte</label>

        <button className="boton atardecer ancho" disabled={enviando}>{enviando ? (progreso || "Publicando…") : "Publicar reporte"}</button>
      </form>

      <div className="caja mapa-selector">
        <div className="lista-cabecera">
          <b style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><MapPin size={18} weight="bold" />Ubicación del incidente</b>
          {gps && <button type="button" className="boton pequeno" onClick={() => { moverPin(gps); setCentrar([...gps]); }}><Crosshair size={16} weight="bold" />Usar mi ubicación</button>}
        </div>
        <p className="nota">Arrastra el pin o toca el mapa si el incidente está en otro lugar.</p>
        <MapContainer center={posicion} zoom={15} className="mapa">
          <TileLayer {...CAPA_MAPA} />
          <Selector posicion={posicion} onCambio={moverPin} />
          <Recentrar punto={centrar} />
        </MapContainer>
      </div>
    </div>
    </>
  );
}
