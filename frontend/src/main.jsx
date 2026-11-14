import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import "./estilos.css";
import App from "./App.jsx";
import { ProveedorSesion } from "./sesion.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  // Sin StrictMode: en desarrollo duplica cada petición y la primera consulta de un
  // detalle aparecería siempre como "caché", lo que confunde en la demo.
  <BrowserRouter>
    <ProveedorSesion>
      <App />
    </ProveedorSesion>
  </BrowserRouter>
);
