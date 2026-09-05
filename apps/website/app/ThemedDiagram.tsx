type Props = {
  light: string;
  dark: string;
  alt: string;
  caption?: string;
  priority?: boolean;
  aspect?: "wide" | "portrait";
  className?: string;
};

export default function ThemedDiagram({ light, dark, alt, caption, aspect = "wide", className = "" }: Props) {
  const isPortrait = aspect === "portrait";

  return <figure className={`themed-diagram ${isPortrait ? "is-portrait" : ""} ${className}`.trim()}>
    <div className="diagram-sprite-frame" role="img" aria-label={alt}>
      <img className="diagram-sprite diagram-sprite-dark" src={dark} alt="" aria-hidden="true" loading="eager" />
      <img className="diagram-sprite diagram-sprite-light" src={light} alt="" aria-hidden="true" loading="eager" />
    </div>
    {caption ? <figcaption>{caption}</figcaption> : null}
  </figure>;
}
