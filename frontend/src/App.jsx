import { Buildings, ClipboardText, FilmStrip, MapTrifold, Newspaper, Plus, SignIn, SignOut } from "@phosphor-icons/react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import Marca from "./componentes/Marca.jsx";
import Creditos from "./paginas/Creditos.jsx";
import Inicio from "./paginas/Inicio.jsx";
import Ingresar from "./paginas/Ingresar.jsx";
import Landing from "./paginas/Landing.jsx";
import MisReportes from "./paginas/MisReportes.jsx";
import NoEncontrada from "./paginas/NoEncontrada.jsx";
import Noticias from "./paginas/Noticias.jsx";
import PanelEntidad from "./paginas/PanelEntidad.jsx";
import Privacidad from "./paginas/Privacidad.jsx";
import Reportar from "./paginas/Reportar.jsx";
import Videos from "./paginas/Videos.jsx";
import { useSesion } from "./sesion.jsx";

function iniciales(nombre) {
  return nombre.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
}

function Cabecera() {
  const { usuario, cerrar } = useSesion();
  const entidad = usuario?.rol === "entidad";
  return (
    <>
      <header className="cabecera">
        <Marca />
        <nav aria-label="Principal">
          <NavLink to="/mapa"><MapTrifold size={18} weight="bold" />Mapa en vivo</NavLink>
          <NavLink to="/noticias"><Newspaper size={18} weight="bold" />Noticias</NavLink>
          <NavLink to="/videos"><FilmStrip size={18} weight="bold" />Videos</NavLink>
          {usuario?.rol === "ciudadano" && <NavLink to="/mis-reportes"><ClipboardText size={18} weight="bold" />Mis reportes</NavLink>}
          {entidad && <NavLink to="/entidad"><Buildings size={18} weight="bold" />Panel de entidad</NavLink>}
          {!entidad && <NavLink to="/reportar" className="cta"><Plus size={18} weight="bold" />Reportar</NavLink>}
          {usuario ? (
            <span className="usuario">
              <span className="avatar" style={{ background: entidad ? "#0B4F6C" : "#2D6A4F" }}>{iniciales(usuario.nombre)}</span>
              {usuario.nombre.split(" ")[0]}
              <button className="enlace" onClick={cerrar} aria-label="Cerrar sesión"><SignOut size={18} weight="bold" /></button>
            </span>
          ) : (
            <NavLink to="/ingresar"><SignIn size={18} weight="bold" />Ingresar</NavLink>
          )}
        </nav>
        {usuario ? (
          <button className="enlace solo-movil" onClick={cerrar} aria-label="Cerrar sesión">
            <span className="avatar" style={{ background: entidad ? "#0B4F6C" : "#2D6A4F" }}>{iniciales(usuario.nombre)}</span>
          </button>
        ) : (
          <NavLink to="/ingresar" className="enlace solo-movil"><SignIn size={20} weight="bold" />Ingresar</NavLink>
        )}
      </header>
      <nav className="barra-movil" aria-label="Principal en móvil">
        <NavLink to="/mapa"><MapTrifold size={22} weight="bold" />Mapa</NavLink>
        <NavLink to="/noticias"><Newspaper size={22} weight="bold" />Noticias</NavLink>
        {entidad
          ? <NavLink to="/entidad" className="mas"><Buildings size={22} weight="bold" />Panel</NavLink>
          : <NavLink to="/reportar" className="mas"><Plus size={22} weight="bold" />Reportar</NavLink>}
        <NavLink to="/videos"><FilmStrip size={22} weight="bold" />Videos</NavLink>
        {usuario?.rol === "ciudadano"
          ? <NavLink to="/mis-reportes"><ClipboardText size={22} weight="bold" />Mis reportes</NavLink>
          : <NavLink to="/ingresar"><SignIn size={22} weight="bold" />Ingresar</NavLink>}
      </nav>
    </>
  );
}

export default function App() {
  const { pathname } = useLocation();
  if (pathname === "/") return <Landing />;
  return (
    <div className="app">
      <a href="#contenido" className="saltar">Saltar al contenido</a>
      <Cabecera />
      <main id="contenido">
        <Routes>
          <Route path="/mapa" element={<Inicio />} />
          <Route path="/noticias" element={<Noticias />} />
          <Route path="/videos" element={<Videos />} />
          <Route path="/reportar" element={<Reportar />} />
          <Route path="/mis-reportes" element={<MisReportes />} />
          <Route path="/entidad" element={<PanelEntidad />} />
          <Route path="/ingresar" element={<Ingresar />} />
          <Route path="/privacidad" element={<Privacidad />} />
          <Route path="/creditos" element={<Creditos />} />
          <Route path="*" element={<NoEncontrada />} />
        </Routes>
      </main>
    </div>
  );
}
