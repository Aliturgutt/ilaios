export default function SystemMotionSignature() {
  const primary = [46, 58, 70, 82, 94, 106];
  const secondary = [118, 130, 142, 154, 166, 178, 190];
  const arcs = [64, 88, 116, 148];

  return <div className="system-motion-signature" aria-hidden="true" data-visual-role="canonical-system-motion">
    <svg viewBox="0 0 420 300" role="presentation" focusable="false">
      <g className="motion-float">
        <g className="motion-guides">
          <ellipse cx="210" cy="198" rx="176" ry="58" />
          <line x1="210" y1="38" x2="210" y2="252" />
        </g>

        <g className="motion-secondary-rings">
          {secondary.map((rx, index) => <ellipse key={rx} className={`secondary-ring phase-${index % 4}`} cx="210" cy="198" rx={rx} ry={Math.max(18, Math.round(rx * 0.31))} />)}
        </g>

        <g className="motion-primary-rings">
          {primary.map((rx, index) => <ellipse key={rx} className={`primary-ring phase-${index % 3}`} cx="210" cy="198" rx={rx} ry={Math.max(16, Math.round(rx * 0.32))} />)}
        </g>

        <g className="motion-orbit-arcs">
          {arcs.map((rx, index) => <ellipse key={rx} className={`orbit-arc orbit-${index + 1}`} cx="210" cy="198" rx={rx} ry={Math.max(18, Math.round(rx * 0.33))} pathLength="100" />)}
        </g>

        <g className="motion-axis">
          <line className="axis-base" x1="210" y1="66" x2="210" y2="236" />
          <line className="axis-pulse" x1="210" y1="82" x2="210" y2="156" />
        </g>

        <g className="motion-markers">
          <circle className="marker marker-a" cx="326" cy="198" r="3" />
          <circle className="marker marker-b" cx="128" cy="178" r="2.6" />
          <circle className="marker marker-c" cx="260" cy="226" r="2.4" />
        </g>

        <g className="motion-cube">
          <g className="cube-body">
            <polygon className="cube-face cube-top" points="210,74 250,94 210,114 170,94" />
            <polygon className="cube-face cube-left" points="170,94 210,114 210,158 170,138" />
            <polygon className="cube-face cube-right" points="210,114 250,94 250,138 210,158" />
          </g>
          <g className="cube-wire">
            <polyline points="210,74 250,94 250,138 210,158 170,138 170,94 210,74" />
            <line x1="210" y1="114" x2="210" y2="158" />
            <line x1="170" y1="94" x2="210" y2="114" />
            <line x1="250" y1="94" x2="210" y2="114" />
          </g>
          <polyline className="cube-highlight" points="210,74 250,94 210,114" />
        </g>

        <g className="motion-core">
          <circle className="core-halo" cx="210" cy="198" r="21" />
          <circle className="core-breath" cx="210" cy="198" r="10" />
          <circle className="core-node" cx="210" cy="198" r="4" />
        </g>
      </g>
    </svg>
  </div>;
}
