export default function SystemMotionSignature() {
  const structuralRings = [52, 70, 92, 118, 146, 174];
  const depthRings = [86, 116, 150];
  const arcs = [66, 92, 122, 156];

  return <div className="system-motion-signature" aria-hidden="true" data-visual-role="canonical-dimensional-orbital-core">
    <svg viewBox="0 0 420 320" role="presentation" focusable="false">
      <g className="motion-float">
        <g className="motion-guides">
          <ellipse cx="210" cy="206" rx="178" ry="60" />
          <line x1="210" y1="34" x2="210" y2="272" />
          <line x1="58" y1="206" x2="362" y2="206" />
        </g>

        <g className="motion-depth-orbits">
          {depthRings.map((rx, index) => <ellipse key={rx} className={`depth-ring depth-${index + 1}`} cx="210" cy="206" rx={rx} ry={Math.round(rx * 0.25)} />)}
        </g>

        <g className="motion-structural-rings">
          {structuralRings.map((rx, index) => <ellipse key={rx} className={`structural-ring phase-${index % 4}`} cx="210" cy="206" rx={rx} ry={Math.max(17, Math.round(rx * 0.31))} />)}
        </g>

        <g className="motion-orbit-arcs">
          {arcs.map((rx, index) => <ellipse key={rx} className={`orbit-arc orbit-${index + 1}`} cx="210" cy="206" rx={rx} ry={Math.max(18, Math.round(rx * 0.32))} pathLength="100" />)}
        </g>

        <g className="motion-axis">
          <line className="axis-base" x1="210" y1="64" x2="210" y2="248" />
          <line className="axis-pulse" x1="210" y1="82" x2="210" y2="160" />
        </g>

        <g className="motion-markers">
          <circle className="marker marker-a" cx="330" cy="206" r="3" />
          <circle className="marker marker-b" cx="132" cy="184" r="2.6" />
          <circle className="marker marker-c" cx="262" cy="236" r="2.4" />
        </g>

        <g className="motion-cube">
          <g className="cube-depth">
            <polygon points="210,72 255,95 210,118 165,95" />
            <polygon points="165,95 210,118 210,166 165,143" />
            <polygon points="210,118 255,95 255,143 210,166" />
          </g>
          <g className="cube-wire">
            <polyline points="210,72 255,95 255,143 210,166 165,143 165,95 210,72" />
            <line x1="210" y1="118" x2="210" y2="166" />
            <line x1="165" y1="95" x2="210" y2="118" />
            <line x1="255" y1="95" x2="210" y2="118" />
          </g>
          <g className="cube-inner">
            <polygon points="210,88 237,102 210,116 183,102" />
            <polyline points="183,102 210,116 237,102" />
          </g>
          <polyline className="cube-highlight" points="210,72 255,95 210,118" />
        </g>

        <g className="motion-core">
          <circle className="core-halo" cx="210" cy="206" r="23" />
          <circle className="core-breath" cx="210" cy="206" r="11" />
          <circle className="core-node" cx="210" cy="206" r="4" />
        </g>
      </g>
    </svg>
  </div>;
}
