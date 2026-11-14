import { renderToStaticMarkup } from "react-dom/server";
import { Dog, Drop, Fire, Question, RoadHorizon, Siren, TrafficSign, Trash, Waves } from "@phosphor-icons/react";

// Un solo set (Phosphor), un solo grosor: así las categorías se leen como sistema y no como emojis sueltos
export const ICONO_CATEGORIA = {
  emergencias: Fire, seguridad: Siren, servicios: Drop, vias: RoadHorizon, transito: TrafficSign,
  ambiente: Trash, animales: Dog, playas: Waves, otro: Question,
};

export function IconoCategoria({ categoria, size = 20, weight = "bold", ...resto }) {
  const Icono = ICONO_CATEGORIA[categoria] || Question;
  return <Icono size={size} weight={weight} aria-hidden="true" {...resto} />;
}

// Versión en texto SVG para los marcadores de Leaflet (divIcon necesita HTML plano)
const cacheSvg = {};
export function svgCategoria(categoria, color, size = 18) {
  const clave = `${categoria}-${color}-${size}`;
  if (!cacheSvg[clave]) {
    const Icono = ICONO_CATEGORIA[categoria] || Question;
    cacheSvg[clave] = renderToStaticMarkup(<Icono size={size} weight="bold" color={color} />);
  }
  return cacheSvg[clave];
}
