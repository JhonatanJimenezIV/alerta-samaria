export default function Privacidad() {
  return (
    <div className="pagina estrecha texto-legal">
      <div className="pagina-cabecera">
        <h1>Tratamiento de datos personales</h1>
        <p>Alerta Samaria es un proyecto académico. Este resumen explica qué datos usa y cómo, según la Ley 1581 de 2012.</p>
      </div>
      <h2>Qué datos se recogen</h2>
      <p>Nombre, correo, teléfono, barrio y dirección al crear la cuenta. Al reportar, la ubicación del incidente y, si lo permites, la ubicación desde donde reportas.</p>
      <h2>Para qué se usan</h2>
      <ul>
        <li>La ubicación del incidente se publica en el mapa. En seguridad se muestra aproximada, a unos 150 metros.</li>
        <li>La ubicación desde donde reportas solo sirve para calcular la confianza del reporte y nunca se publica.</li>
        <li>Tu contacto solo lo ve la entidad responsable y únicamente si lo autorizas en ese reporte.</li>
      </ul>
      <h2>Tus derechos</h2>
      <p>Puedes conocer, actualizar y pedir que se eliminen tus datos. Si borras tu cuenta, tus reportes se conservan sin datos personales para no perder las estadísticas.</p>
      <h2>Emergencias</h2>
      <p>La plataforma informa a la comunidad pero no reemplaza a los organismos de socorro. Si hay riesgo para la vida, llama al 123.</p>
    </div>
  );
}
