// Fotos y videos de un reporte (las URLs son prefirmadas de S3 y vencen en 1 hora)
export default function Galeria({ media }) {
  if (!media?.length) return null;
  return (
    <div className={`galeria ${media.length === 1 ? "una" : ""}`}>
      {media.map((m) => (m.clase === "video"
        ? <video key={m.id} src={m.url} controls playsInline preload="metadata" aria-label="Video adjunto al reporte" />
        : <a key={m.id} href={m.url} target="_blank" rel="noreferrer"><img src={m.url} alt="Foto adjunta al reporte" loading="lazy" /></a>))}
    </div>
  );
}
