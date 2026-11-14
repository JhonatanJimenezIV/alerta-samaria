export const CENTRO_SANTA_MARTA = [11.2290, -74.2000];

// Coordenadas aproximadas de barrios y corregimientos (para centrar el pin y sugerir el barrio)
export const BARRIOS = [
  { nombre: "Centro Histórico", comuna: "Comuna 2", lat: 11.2420, lng: -74.2110 },
  { nombre: "Pescaíto", comuna: "Comuna 1", lat: 11.2480, lng: -74.2050 },
  { nombre: "Bastidas", comuna: "Comuna 1", lat: 11.2530, lng: -74.1980 },
  { nombre: "El Prado", comuna: "Comuna 3", lat: 11.2350, lng: -74.2020 },
  { nombre: "Santa Fe", comuna: "Comuna 4", lat: 11.2350, lng: -74.1950 },
  { nombre: "Los Almendros", comuna: "Comuna 5", lat: 11.2230, lng: -74.1880 },
  { nombre: "Mamatoco", comuna: "Comuna 6", lat: 11.2280, lng: -74.1650 },
  { nombre: "El Rodadero", comuna: "Comuna 8", lat: 11.2050, lng: -74.2270 },
  { nombre: "Gaira", comuna: "Comuna 8", lat: 11.1930, lng: -74.2240 },
  { nombre: "Pozos Colorados", comuna: "Comuna 8", lat: 11.1650, lng: -74.2250 },
  { nombre: "Taganga", comuna: "Corregimiento Taganga", lat: 11.2670, lng: -74.1900 },
  { nombre: "Bonda", comuna: "Corregimiento Bonda", lat: 11.2350, lng: -74.1300 },
  { nombre: "Minca", comuna: "Corregimiento Minca", lat: 11.1430, lng: -74.1180 },
];

export const URGENCIA = {
  1: { nombre: "Alta", color: "#E8553A" },
  2: { nombre: "Media", color: "#C78A00" },
  3: { nombre: "Baja", color: "#2D6A4F" },
};

export const ESTADOS = {
  pendiente: { nombre: "Pendiente", color: "#8A99A6" },
  confirmado: { nombre: "Confirmado", color: "#0B4F6C" },
  en_atencion: { nombre: "En atención", color: "#C78A00" },
  resuelto: { nombre: "Resuelto", color: "#2D6A4F" },
};

export const NOMBRES_CATEGORIA = {
  emergencias: "Emergencias", seguridad: "Seguridad", servicios: "Servicios públicos", vias: "Vías",
  transito: "Tránsito", ambiente: "Ambiente", animales: "Animales", playas: "Playas", otro: "Otro",
};

export function barrioMasCercano(lat, lng) {
  let mejor = BARRIOS[0];
  let menor = Infinity;
  for (const b of BARRIOS) {
    const d = (b.lat - lat) ** 2 + (b.lng - lng) ** 2;
    if (d < menor) { menor = d; mejor = b; }
  }
  return mejor;
}

export function haceCuanto(iso) {
  const seg = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seg < 60) return "hace un momento";
  if (seg < 3600) return `hace ${Math.floor(seg / 60)} min`;
  if (seg < 86400) return `hace ${Math.floor(seg / 3600)} h`;
  return `hace ${Math.floor(seg / 86400)} d`;
}
