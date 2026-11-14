import { CheckCircle, List, MapPin, Phone, UsersThree, X } from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Marca from "../componentes/Marca.jsx";
import { haceCuanto } from "../constantes.js";
import { FOTOS, urlFoto } from "../fotos.js";
import { IconoCategoria } from "../iconos.jsx";
import "../landing.css";

const PARADAS = [
  {
    foto: "rodaderoCalle", categoria: "vias", nombre: "Vías y tránsito", lugar: "El Rodadero",
    titulo: "Cuando llueve, la calle cambia en minutos",
    texto: "Reporta una calle inundada o un arroyo y aparece en el mapa de quien va a pasar por ahí. Se retira sola a las 12 horas, cuando deja de ser noticia.",
  },
  {
    foto: "obras", categoria: "servicios", nombre: "Servicios públicos", lugar: "Centro",
    titulo: "Una tubería rota se reporta una sola vez",
    texto: "Los vecinos confirman con un toque en lugar de repetir el mismo reporte. La empresa de servicios lo recibe con la dirección exacta y un punto de referencia.",
  },
  {
    foto: "taganga", categoria: "emergencias", nombre: "Emergencias", lugar: "Taganga",
    titulo: "Primero el 123. Después, que todos se enteren",
    texto: "Un incendio en los cerros o un cable caído muestran siempre la línea de emergencias y llegan a las entidades al instante.",
  },
  {
    foto: "peatonal", categoria: "seguridad", nombre: "Seguridad", lugar: "Centro Histórico",
    titulo: "Avisar sin exponerte",
    texto: "En seguridad el mapa muestra la zona aproximada, a unos 150 metros. Nunca tu nombre ni el punto exacto desde donde reportaste.",
  },
];

const PASOS = [
  { titulo: "Reporta con tu ubicación", texto: "El GPS pone el pin; lo arrastras si el problema está en otra cuadra. Eliges qué pasa y agregas un punto de referencia." },
  { titulo: "Tus vecinos lo confirman", texto: "Con tres confirmaciones el reporte pasa a confirmado. Si nadie lo confirma en 48 horas, se elimina solo." },
  { titulo: "La entidad lo atiende", texto: "La entidad responsable lo toma y cambia su estado. Todos ven el avance, desde pendiente hasta resuelto." },
];

const PREGUNTAS = [
  ["¿Necesito una cuenta para ver los reportes?", "No. El mapa, el feed y las noticias son públicos, porque en una emergencia nadie debería tener que registrarse para informarse. La cuenta solo se pide para reportar y confirmar."],
  ["¿Quién ve mi nombre cuando reporto?", "Nadie en el mapa público: aparece como usuario verificado o anónimo. La entidad responsable solo ve tu contacto si lo autorizas en ese reporte."],
  ["¿Esto reemplaza al 123?", "No. Si hay riesgo para la vida, llama primero al 123. Alerta Samaria sirve para que la comunidad sepa lo que pasa y para que las entidades lo atiendan con datos precisos."],
  ["¿Cómo se evitan los reportes falsos?", "Cada reporte necesita confirmaciones de otros vecinos, cada cuenta tiene un límite de reportes por hora y lo que nadie confirma en 48 horas desaparece."],
  ["¿Cuánto tiempo se ve un reporte en el mapa?", "Depende de lo que pasa: una calle inundada se ve 12 horas, un corte de agua 3 días y un semáforo dañado 7 días. El historial queda guardado para las estadísticas."],
  ["¿Qué hacen con mis datos?", "Se tratan según la Ley 1581 de 2012. Tu ubicación solo se usa para dar confianza al reporte y nunca se publica."],
  ["¿Qué entidades reciben los reportes?", "Las que tengan una cuenta de entidad en la plataforma, cada una con las categorías que atiende. En esta versión de demostración son entidades de ejemplo."],
];

const TAGLINE = "Santa Marta se cuida mejor cuando todos vemos lo mismo, al mismo tiempo.";

function useReveal() {
  // Cada sección sube 32 px y aparece una sola vez al entrar en pantalla (IntersectionObserver, no scroll listeners)
  useEffect(() => {
    const els = document.querySelectorAll(".lp [data-reveal]");
    const io = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("visible"); io.unobserve(e.target); } });
    }, { threshold: 0.15 });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}

function Nav() {
  const [abierto, setAbierto] = useState(false);
  const enlaces = [["Mapa en vivo", "/mapa"], ["Noticias", "/noticias"], ["Cómo funciona", "#como-funciona"], ["Para entidades", "#entidades"]];
  return (
    <header className={`lp-nav ${abierto ? "abierto" : ""}`}>
      <Marca claro />
      <nav className="lp-nav-enlaces" aria-label="Principal">
        {enlaces.map(([t, h]) => (h.startsWith("#") ? <a key={h} href={h}>{t}</a> : <Link key={h} to={h}>{t}</Link>))}
      </nav>
      <div className="lp-nav-acciones">
        <Link to="/ingresar" className="lp-enlace">Ingresar</Link>
        <Link to="/reportar" className="lp-boton">Reportar</Link>
        <button className="lp-menu" aria-label={abierto ? "Cerrar menú" : "Abrir menú"} aria-expanded={abierto} onClick={() => setAbierto(!abierto)}>
          {abierto ? <X size={22} weight="bold" /> : <List size={22} weight="bold" />}
        </button>
      </div>
      {abierto && (
        <div className="lp-panel-movil">
          {enlaces.map(([t, h], i) => (h.startsWith("#")
            ? <a key={h} href={h} style={{ "--i": i }} onClick={() => setAbierto(false)}>{t}</a>
            : <Link key={h} to={h} style={{ "--i": i }}>{t}</Link>))}
          <Link to="/ingresar" style={{ "--i": 4 }}>Ingresar</Link>
        </div>
      )}
    </header>
  );
}

function Recorrido({ conteos }) {
  const [activa, setActiva] = useState(0);
  const refs = useRef([]);
  useEffect(() => {
    const io = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => { if (e.isIntersecting) setActiva(Number(e.target.dataset.i)); });
    }, { rootMargin: "-45% 0px -45% 0px" });
    refs.current.forEach((el) => el && io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <section className="lp-recorrido" aria-label="Qué puedes reportar">
      <div className="lp-recorrido-fotos" aria-hidden="true">
        {PARADAS.map((p, i) => (
          <img key={p.foto} src={urlFoto(p.foto, 1280)} alt="" className={i === activa ? "activa" : ""} loading="lazy" decoding="async" />
        ))}
        <span className="lp-credito">{FOTOS[PARADAS[activa].foto].lugar}. Foto: {FOTOS[PARADAS[activa].foto].autor}</span>
      </div>
      <div className="lp-recorrido-textos">
        {PARADAS.map((p, i) => (
          <article key={p.foto} className={`lp-parada ${i === activa ? "activa" : ""}`} data-i={i} ref={(el) => (refs.current[i] = el)}>
            <img className="lp-parada-foto" src={urlFoto(p.foto, 960)} alt={FOTOS[p.foto].lugar} loading="lazy" />
            <div className="lp-parada-cat">
              <IconoCategoria categoria={p.categoria} size={22} />
              <span>{p.nombre}</span>
              <span className="lp-parada-lugar">{p.lugar}</span>
            </div>
            <h3>{p.titulo}</h3>
            <p>{p.texto}</p>
            {conteos && (
              <p className="lp-parada-vivo" aria-live="polite">
                {conteos[p.categoria] ? `${conteos[p.categoria]} ${conteos[p.categoria] === 1 ? "reporte activo" : "reportes activos"} de ${p.nombre.toLowerCase()} ahora` : `Sin reportes activos de ${p.nombre.toLowerCase()} en este momento`}
              </p>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function Tagline() {
  const ref = useRef(null);
  const palabras = useMemo(() => TAGLINE.split(" "), []);
  const [encendidas, setEncendidas] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setEncendidas(palabras.length); return; }
    let pendiente = false;
    const calcular = () => {
      pendiente = false;
      const r = ref.current.getBoundingClientRect();
      const vh = window.innerHeight;
      // progreso 0 → 1 mientras el bloque cruza del 85 % al 35 % de la pantalla
      const p = Math.min(1, Math.max(0, (vh * 0.85 - r.top) / (vh * 0.5 + r.height * 0.5)));
      setEncendidas(Math.round(p * palabras.length));
    };
    const alScroll = () => { if (!pendiente) { pendiente = true; requestAnimationFrame(calcular); } };
    window.addEventListener("scroll", alScroll, { passive: true });
    calcular();
    return () => window.removeEventListener("scroll", alScroll);
  }, [palabras.length]);
  return (
    <section className="lp-tagline" ref={ref}>
      <p aria-label={TAGLINE}>
        {palabras.map((w, i) => <span key={i} className={i < encendidas ? "on" : ""} aria-hidden="true">{w} </span>)}
      </p>
    </section>
  );
}

export default function Landing() {
  const [feed, setFeed] = useState(null);
  useReveal();
  useEffect(() => { api("/reportes/feed?limite=200").then(setFeed).catch(() => setFeed(null)); }, []);

  const conteos = useMemo(() => {
    if (!feed) return null;
    const c = {};
    feed.reportes.forEach((r) => { c[r.categoria] = (c[r.categoria] || 0) + 1; });
    return c;
  }, [feed]);
  const ejemplo = feed?.reportes.find((r) => r.estado === "en_atencion") || feed?.reportes[0];

  return (
    <div className="lp">
      <a href="#contenido" className="saltar">Saltar al contenido</a>
      <Nav />

      <main id="contenido">
        {/* Hero */}
        <section className="lp-hero">
          <img src={urlFoto("marina", 1920)} alt="La marina de Santa Marta con edificios y la Sierra al fondo" className="lp-hero-foto" fetchpriority="high" />
          <div className="lp-hero-velo" aria-hidden="true" />
          <div className="lp-hero-contenido">
            <h1>Sabe qué pasa en tu barrio<br />antes de salir de casa</h1>
            <p>Calles inundadas, cortes de agua, semáforos dañados y robos. Lo reportan vecinos verificados y lo atienden las entidades de Santa Marta.</p>
            <div className="lp-hero-acciones">
              <Link to="/mapa" className="lp-boton grande"><MapPin size={20} weight="bold" />Ver el mapa en vivo</Link>
              {feed && (
                <span className="lp-vivo"><i aria-hidden="true" />{feed.total} {feed.total === 1 ? "incidente activo" : "incidentes activos"} en este momento</span>
              )}
            </div>
          </div>
          <span className="lp-credito hero">{FOTOS.marina.lugar}. Foto: {FOTOS.marina.autor}, {FOTOS.marina.licencia}</span>
        </section>

        <section className="lp-intro" data-reveal>
          <h2>Una red de vecinos para lo que pasa en la calle</h2>
          <p>Hoy los avisos se pierden entre grupos de WhatsApp y publicaciones que nadie verifica. Aquí cada reporte tiene ubicación, se confirma entre vecinos y le llega a quien lo tiene que resolver.</p>
        </section>

        <Recorrido conteos={conteos} />

        <Tagline />

        {/* Cómo funciona */}
        <section className="lp-como" id="como-funciona">
          <div className="lp-como-texto" data-reveal>
            <h2>Así funciona</h2>
            <ol>
              {PASOS.map((p) => (<li key={p.titulo}><h3>{p.titulo}</h3><p>{p.texto}</p></li>))}
            </ol>
          </div>
          <div className="lp-como-ejemplo" data-reveal>
            <p className="lp-ejemplo-titulo">Así se ve un reporte real del mapa</p>
            {ejemplo ? (
              <Link to={`/mapa?r=${ejemplo.id}`} className="lp-reporte">
                <div className="lp-reporte-cab">
                  <span className="lp-reporte-icono"><IconoCategoria categoria={ejemplo.categoria} size={22} /></span>
                  <div>
                    <strong>{ejemplo.subtipo_nombre}</strong>
                    <span>{ejemplo.barrio}, {haceCuanto(ejemplo.creado_en)}</span>
                  </div>
                </div>
                {ejemplo.descripcion && <p>{ejemplo.descripcion}</p>}
                <div className="lp-reporte-pie">
                  <span><UsersThree size={18} weight="bold" />{ejemplo.confirmaciones} confirmaciones</span>
                  <span className={`lp-estado ${ejemplo.estado}`}>{{ pendiente: "Pendiente", confirmado: "Confirmado", en_atencion: "En atención", resuelto: "Resuelto" }[ejemplo.estado]}</span>
                </div>
              </Link>
            ) : (
              <div className="lp-reporte vacio">Cuando el servidor esté en línea, aquí verás un reporte real del mapa.</div>
            )}
          </div>
        </section>

        {/* Entidades */}
        <section className="lp-entidades" id="entidades">
          <img src={urlFoto("vistaSierra", 1280)} alt={FOTOS.vistaSierra.lugar} loading="lazy" data-reveal />
          <div data-reveal>
            <h2>Para la Alcaldía y las empresas de servicios</h2>
            <p>Un panel con los reportes de las categorías que atiende cada entidad, listos para despachar.</p>
            <ul>
              <li><CheckCircle size={22} weight="bold" /><span><b>Ubicación exacta</b> con dirección, referencia y contacto del ciudadano cuando lo autoriza.</span></li>
              <li><CheckCircle size={22} weight="bold" /><span><b>Ordenados por urgencia,</b> para atender primero lo que pone vidas o vías en riesgo.</span></li>
              <li><CheckCircle size={22} weight="bold" /><span><b>Puntos de riesgo por barrio</b> que cruzan robos con alumbrado dañado.</span></li>
              <li><CheckCircle size={22} weight="bold" /><span><b>Estadísticas por día y barrio</b> para decidir dónde invertir.</span></li>
            </ul>
            <Link to="/ingresar" className="lp-boton secundario">Probar el panel de demostración</Link>
          </div>
        </section>

        {/* Preguntas */}
        <section className="lp-faq" data-reveal>
          <h2>Preguntas frecuentes</h2>
          <dl>
            {PREGUNTAS.map(([q, a]) => (<div key={q}><dt>{q}</dt><dd>{a}</dd></div>))}
          </dl>
        </section>

        {/* Cierre */}
        <section className="lp-final" data-reveal>
          <img src={urlFoto("atardecer", 1280)} alt={FOTOS.atardecer.lugar} loading="lazy" />
          <div>
            <h2>Mira qué está pasando<br />en Santa Marta ahora</h2>
            <Link to="/mapa" className="lp-boton grande"><MapPin size={20} weight="bold" />Ver el mapa en vivo</Link>
            <p className="lp-aviso"><Phone size={18} weight="bold" />Si hay riesgo para la vida, llama primero al 123.</p>
          </div>
        </section>
      </main>

      <footer className="lp-pie">
        <Marca />
        <nav aria-label="Pie de página">
          <Link to="/mapa">Mapa</Link><Link to="/noticias">Noticias</Link><Link to="/reportar">Reportar</Link>
          <Link to="/privacidad">Privacidad</Link><Link to="/creditos">Créditos de las fotos</Link>
        </nav>
        <p>Proyecto académico de Bases de Datos NoSQL, Universidad del Magdalena.</p>
      </footer>
    </div>
  );
}
