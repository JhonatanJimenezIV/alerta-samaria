import { Link } from "react-router-dom";

// Marca: la bahía vista como un pin. Sierra (verde), mar (azul), sol del atardecer y franja tayrona (oro).
export function Simbolo({ size = 30 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 1C9 1 4 6.3 4 12.8 4 21.5 16 31 16 31s12-9.5 12-18.2C28 6.3 23 1 16 1z" fill="#0B4F6C" />
      <path d="M7.5 16.5l4-4.5 3 3 3.5-5 6.5 6.5c-.6 1.6-1.4 3.1-2.3 4.5H9.6c-.8-1.4-1.5-2.9-2.1-4.5z" fill="#2D6A4F" />
      <path d="M9.6 21h12.8c-1.9 2.9-4.3 5.3-6.4 7.1-2.1-1.8-4.5-4.2-6.4-7.1z" fill="#E0A526" />
      <circle cx="21" cy="8.5" r="2.6" fill="#E8553A" />
    </svg>
  );
}

export default function Marca({ claro = false }) {
  return (
    <Link to="/" className={`marca ${claro ? "claro" : ""}`} aria-label="Alerta Samaria, inicio">
      <Simbolo />
      <span>Alerta Samaria</span>
    </Link>
  );
}
