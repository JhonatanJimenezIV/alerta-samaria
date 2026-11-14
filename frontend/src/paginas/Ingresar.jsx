import { useEffect, useState } from "react";
import { Buildings, User } from "@phosphor-icons/react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { BARRIOS } from "../constantes.js";
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

  return (
    <div className="pagina estrecha">
      <div className="pagina-cabecera"><h1>Ingresar</h1><p>Para ver el mapa no necesitas cuenta. Para reportar y confirmar incidentes, sí.</p></div>
      {error && <p className="error">{error}</p>}

      <div className="dos-columnas">
        <form className="caja" onSubmit={registrar}>
          <h2>Crear cuenta</h2>
          <label>Nombre completo<input required minLength={3} {...campo("nombre")} /></label>
          <label>Correo<input type="email" required {...campo("email")} /></label>
          <label>Teléfono<input {...campo("telefono")} /></label>
          <label>Barrio
            <select {...campo("barrio")}>
              <option value="">Selecciona…</option>
              {BARRIOS.map((b) => <option key={b.nombre}>{b.nombre}</option>)}
            </select>
          </label>
          <label>Dirección (opcional)<input {...campo("direccion")} /></label>
          <label className="check">
            <input type="checkbox" checked={form.acepta_politica}
                   onChange={(e) => setForm({ ...form, acepta_politica: e.target.checked })} />
            Autorizo el tratamiento de mis datos personales y de mi ubicación según la Ley 1581 de 2012.
            Mis datos nunca se publican; solo se comparten con la entidad si yo lo autorizo en cada reporte.
          </label>
          <button className="boton primario ancho" disabled={cargando}>Crear cuenta</button>
        </form>

        <div className="caja">
          <h2>Usuarios de demostración</h2>
          {!demo && <p className="nota">Ejecuta <code>python scripts/seed.py</code> en cdk-dev para crearlos.</p>}
          {demo && (
            <>
              <h3 className="subtitulo">Ciudadanos</h3>
              {Object.entries(demo.ciudadanos).map(([nombre, id]) => (
                <button key={id} className="boton fila" onClick={() => entrarCon(id)} disabled={cargando}><User size={18} weight="bold" />{nombre}</button>
              ))}
              <h3 className="subtitulo">Entidades</h3>
              {Object.entries(demo.entidades).map(([nombre, id]) => (
                <button key={id} className="boton fila" onClick={() => entrarCon(id)} disabled={cargando}><Buildings size={18} weight="bold" />{nombre}</button>
              ))}
            </>
          )}
          <h3 className="subtitulo">Entrar con un id</h3>
          <div className="en-linea">
            <input placeholder="Id de usuario" value={idManual} onChange={(e) => setIdManual(e.target.value.trim())} />
            <button className="boton" onClick={() => idManual && entrarCon(idManual)} disabled={cargando}>Entrar</button>
          </div>
        </div>
      </div>
    </div>
  );
}
