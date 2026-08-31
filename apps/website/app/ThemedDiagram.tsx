import type { CSSProperties } from "react";

type Props = {
  light: string;
  dark: string;
  alt: string;
  caption?: string;
  priority?: boolean;
  aspect?: "wide" | "portrait";
  className?: string;
};

const WIDE_ROWS: Record<string, number> = {
  "general-flow": 0,
  governance: 1,
  verification: 2,
  "factory-orchestration": 3,
  web: 4,
  video: 5,
  software: 6,
  app: 7,
};

function wideKey(path: string) {
  const file = path.split("/").pop() ?? "";
  return file.replace(/-(dark|light)\.(avif|webp|png)$/i, "");
}

export default function ThemedDiagram({ dark, alt, caption, aspect = "wide", className = "" }: Props) {
  const isPortrait = aspect === "portrait";
  const row = isPortrait ? 0 : WIDE_ROWS[wideKey(dark)];
  if (!isPortrait && row === undefined) {
    throw new Error(`Unknown ILAIOS diagram sprite key: ${wideKey(dark)}`);
  }

  const darkPosition = isPortrait ? 0 : (row / 15) * 100;
  const lightPosition = isPortrait ? 100 : ((row + 8) / 15) * 100;
  const darkStyle = { "--diagram-position": `${darkPosition}%` } as CSSProperties;
  const lightStyle = { "--diagram-position": `${lightPosition}%` } as CSSProperties;

  return <figure className={`themed-diagram ${isPortrait ? "is-portrait" : ""} ${className}`.trim()}>
    <div className="diagram-sprite-frame" role="img" aria-label={alt}>
      <div className={`diagram-sprite diagram-sprite-dark${isPortrait ? " is-intake" : ""}`} style={darkStyle} aria-hidden="true" />
      <div className={`diagram-sprite diagram-sprite-light${isPortrait ? " is-intake" : ""}`} style={lightStyle} aria-hidden="true" />
    </div>
    {caption ? <figcaption>{caption}</figcaption> : null}
  </figure>;
}
