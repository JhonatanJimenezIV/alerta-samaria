// Fotos y videos de un reporte (las URLs son prefirmadas de S3 y vencen en 1 hora)
export function Credito({ credito }) {
  if (!credito) return null;
  return (
    <p className="credito-media">
      {credito.ejemplo && <b>Video de ejemplo para la demostración. </b>}
      <a href={credito.url} target="_blank" rel="noreferrer">{credito.titulo}</a>, de {credito.autor} ({credito.fuente}, {credito.licencia})
    </p>
  );
}

export default function Galeria({ media }) {
  if (!media?.length) return null;
  return (
    <div className={`galeria ${media.length === 1 ? "una" : ""}`}>
      {media.map((m) => (
        <figure key={m.id}>
          {m.clase === "video"
            ? <video src={m.url} controls playsInline preload="metadata" aria-label="Video adjunto al reporte" />
            : <a href={m.url} target="_blank" rel="noreferrer"><img src={m.url} alt="Foto adjunta al reporte" loading="lazy" /></a>}
          <Credito credito={m.credito} />
        </figure>
      ))}
    </div>
  );
}
