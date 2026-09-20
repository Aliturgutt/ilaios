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
    <>
      <figure className={`supplied-visual ${className}`.trim()}>
        <div className="supplied-visual-frame" role="img" aria-label={alt}>
          <img className="supplied-visual-image supplied-visual-dark" src={dark} width={1672} height={941} loading={loading} decoding="async" alt="" aria-hidden="true" />
          <img className="supplied-visual-image supplied-visual-light" src={light} width={1672} height={941} loading={loading} decoding="async" alt="" aria-hidden="true" />
        </div>
        <figcaption>{caption}</figcaption>
      </figure>
      <style>{`
        .supplied-visual{margin:0;border:1px solid var(--line);border-radius:22px;overflow:hidden;background:var(--v2-surface-strong)}
        .supplied-visual-frame{position:relative;aspect-ratio:1672/941;background:var(--v2-surface-strong)}
        .supplied-visual-image{display:block;width:100%;height:auto;aspect-ratio:1672/941;object-fit:contain}
        .supplied-visual-light{display:none}
        html[data-theme="light"] .supplied-visual-dark{display:none}
        html[data-theme="light"] .supplied-visual-light{display:block}
        .supplied-visual figcaption{padding:14px 18px 16px;border-top:1px solid var(--line);color:var(--muted);font-size:.86rem;line-height:1.55}
        @media(max-width:760px){.supplied-visual{border-radius:14px}.supplied-visual figcaption{padding:12px 14px 14px}}
      `}</style>
    </>
  );
}
