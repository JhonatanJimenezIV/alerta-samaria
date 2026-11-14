import { useEffect, useState } from "react";
import { Buildings, User } from "@phosphor-icons/react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { BARRIOS } from "../constantes.js";
import { FOTOS, urlFoto } from "../fotos.js";
import { useSesion } from "../sesion.jsx";

export default function Ingresar() {
  const { iniciar } = useSesion();
  const navegar = useNavigate();
  const [demo, setDemo] = useState(null);
  const [idManual, setIdManual] = useState("");
  const [form, setForm] = useState({ nombre: "", email: "", telefono: "", barrio: "", direccion: "", acepta_politica: false });
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    // seed.py deja aquí los usuarios de demostración
    fetch("/usuarios_demo.json").then((r) => (r.ok ? r.json() : null)).then(setDemo).catch(() => {});
  }, []);

  const entrarCon = async (id) => {
    setError("");
    setCargando(true);
    try {
      const perfil = await api(`/usuarios/${id}`, { usuarioId: id });
      iniciar(perfil);
      navegar(perfil.rol === "entidad" ? "/entidad" : "/mapa");
    } catch (e) {
      setError(e.status === 401 ? "Ese usuario no existe (¿reiniciaste el emulador? vuelve a correr seed.py)" : e.message);
    } finally {
      setCargando(false);
    }
  };

  const registrar = async (e) => {
    e.preventDefault();
    setError("");
    setCargando(true);
    try {
      const perfil = await api("/usuarios", { metodo: "POST", body: form });
      iniciar(perfil);
      navegar("/mapa");
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  const campo = (k) => ({ value: form[k], onChange: (e) => setForm({ ...form, [k]: e.target.value }) });

  const [pestana, setPestana] = useState("demo");
  const iniciales = (n) => n.split(" ").slice(0, 2).map((p) => p[0]).join("");

  return (
    <div className="ingresar">
      <section className="ingresar-foto">
        <img src={urlFoto("marinaBarcos", 1600)} alt="" />
        <div className="ingresar-foto-texto">
          <h1>Reporta lo que ves.<br />Tus vecinos lo confirman.</h1>
          <p>Ver el mapa no requiere cuenta. Para reportar y confirmar incidentes, sí: así cada reporte tiene a alguien verificado detrás.</p>
        </div>
        <span className="pagina-hero-credito">{FOTOS.marinaBarcos.lugar}. Foto: {FOTOS.marinaBarcos.autor}, {FOTOS.marinaBarcos.licencia}</span>
      </section>

      <section className="ingresar-panel">
        <div className="modo">
          <button className={pestana === "demo" ? "activo" : ""} onClick={() => setPestana("demo")}>Usuarios de demostración</button>
          <button className={pestana === "nueva" ? "activo" : ""} onClick={() => setPestana("nueva")}>Crear cuenta</button>
        </div>
        {error && <p className="error" style={{ marginTop: 16 }}>{error}</p>}

        {pestana === "demo" ? (
          <div className="ingresar-demo">
            {!demo && <p className="nota">Ejecuta <code>python scripts/seed.py</code> en cdk-dev para crearlos.</p>}
            {demo && (
              <>
                <h2>Entra como un vecino</h2>
                <div className="perfiles">
                  {Object.entries(demo.ciudadanos).map(([nombre, id]) => (
                    <button key={id} className="perfil" onClick={() => entrarCon(id)} disabled={cargando}>
                      <span className="avatar" style={{ background: "#2D6A4F" }}>{iniciales(nombre)}</span>
                      <span>{nombre}</span>
                    </button>
                  ))}
                </div>
                <h2>O como una entidad</h2>
                <div className="perfiles">
                  {Object.entries(demo.entidades).map(([nombre, id]) => (
                    <button key={id} className="perfil" onClick={() => entrarCon(id)} disabled={cargando}>
                      <span className="avatar" style={{ background: "#0B4F6C" }}><Buildings size={16} weight="bold" /></span>
                      <span>{nombre}</span>
                    </button>
                  ))}
                </div>
              </>
            )}
            <details className="id-manual">
              <summary>Entrar con un id</summary>
              <div className="en-linea">
                <input placeholder="Id de usuario" value={idManual} onChange={(e) => setIdManual(e.target.value.trim())} />
                <button className="boton" onClick={() => idManual && entrarCon(idManual)} disabled={cargando}><User size={18} weight="bold" />Entrar</button>
              </div>
            </details>
          </div>
        ) : (
          <form onSubmit={registrar} className="ingresar-form">
            <label>Nombre completo<input required minLength={3} autoComplete="name" {...campo("nombre")} /></label>
            <label>Correo<input type="email" required autoComplete="email" {...campo("email")} /></label>
            <div className="dos-columnas">
              <label>Teléfono<input autoComplete="tel" {...campo("telefono")} /></label>
              <label>Barrio
                <select {...campo("barrio")}>
                  <option value="">Selecciona…</option>
                  {BARRIOS.map((b) => <option key={b.nombre}>{b.nombre}</option>)}
                </select>
              </label>
            </div>
            <label>Dirección (opcional)<input autoComplete="street-address" {...campo("direccion")} /></label>
            <label className="check">
              <input type="checkbox" checked={form.acepta_politica}
                     onChange={(e) => setForm({ ...form, acepta_politica: e.target.checked })} />
              <span>Autorizo el tratamiento de mis datos personales y de mi ubicación según la Ley 1581 de 2012.
              Mis datos nunca se publican; solo se comparten con la entidad si yo lo autorizo en cada reporte.</span>
            </label>
            <button className="boton atardecer ancho" disabled={cargando}>Crear cuenta</button>
          </form>
        )}
      </section>
    </div>
  );
}
