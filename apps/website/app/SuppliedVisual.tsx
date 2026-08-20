type Props = {
  light: string;
  dark: string;
  alt: string;
  caption: string;
  priority?: boolean;
  className?: string;
};

export default function SuppliedVisual({ light, dark, alt, caption, priority = false, className = "" }: Props) {
  const loading = priority ? "eager" : "lazy";
  return (
    <figure className={`supplied-visual ${className}`.trim()}>
      <div className="supplied-visual-frame" role="img" aria-label={alt}>
        <img className="supplied-visual-image supplied-visual-dark" src={dark} width={1672} height={941} loading={loading} decoding="async" alt="" aria-hidden="true" />
        <img className="supplied-visual-image supplied-visual-light" src={light} width={1672} height={941} loading={loading} decoding="async" alt="" aria-hidden="true" />
      </div>
      <figcaption>{caption}</figcaption>
    </figure>
  );
}
