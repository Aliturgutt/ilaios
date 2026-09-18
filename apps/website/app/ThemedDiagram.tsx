type Props = {
  light: string;
  dark: string;
  alt: string;
  caption?: string;
  priority?: boolean;
  aspect?: "wide" | "portrait";
  className?: string;
};

/*
 * The former native workflow-node renderer replaced missing visual assets with
 * a second text-heavy workflow presentation. Factory pages already carry their
 * workflow and readiness in accessible page copy, so the rejected duplicate
 * diagram is intentionally retired. Keep the component boundary while callers
 * are migrated independently; this avoids broken asset fallbacks and preserves
 * the existing page contracts without introducing synthetic visuals.
 */
export default function ThemedDiagram({ caption, className = "" }: Props) {
  if (!caption) return null;
  return <p className={`diagram-caption ${className}`.trim()}>{caption}</p>;
}
