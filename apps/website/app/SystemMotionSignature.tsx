export default function SystemMotionSignature() {
  const primary = [36, 48, 60, 72, 84, 96];
  const secondary = [28, 42, 56, 70, 84, 98, 112];

  return (
    <div className="system-motion-signature" data-visual-role="canonical-system-motion" aria-hidden="true">
      <svg viewBox="0 0 360 260" role="presentation" focusable="false">
        <g className="sms-float">
          <g className="sms-guides">
            <path d="M180 26V232" />
            <path d="M66 130H294" />
          </g>

          <g className="sms-secondary-rings">
            {secondary.map((rx, index) => (
              <ellipse key={rx} className={`sms-secondary sms-secondary-${index + 1}`} cx="180" cy={157} rx={rx} ry={Math.max(9, rx * 0.24)} />
            ))}
          </g>

          <g className="sms-primary-rings">
            {primary.map((rx, index) => (
              <ellipse key={rx} className={`sms-primary sms-primary-${index + 1}`} cx="180" cy={150} rx={rx} ry={Math.max(10, rx * 0.27)} />
            ))}
          </g>

          <g className="sms-arcs sms-arc-a"><path d="M96 150a84 24 0 0 1 168 0" /></g>
          <g className="sms-arcs sms-arc-b"><path d="M110 166a70 19 0 0 0 140 0" /></g>
          <g className="sms-arcs sms-arc-c"><path d="M122 141a58 16 0 0 1 116 0" /></g>
          <g className="sms-arcs sms-arc-d"><path d="M135 177a45 13 0 0 0 90 0" /></g>

          <g className="sms-axis">
            <path className="sms-axis-line" d="M180 58V205" />
            <path className="sms-axis-pulse" d="M180 58V205" />
          </g>

          <g className="sms-cube">
            <path className="sms-cube-face sms-face-top" d="M180 66 219 86 180 107 141 86Z" />
            <path className="sms-cube-face sms-face-left" d="M141 86 180 107 180 151 141 129Z" />
            <path className="sms-cube-face sms-face-right" d="M219 86 180 107 180 151 219 129Z" />
            <path className="sms-cube-edge" d="M180 66 219 86 219 129 180 151 141 129 141 86Z" />
            <path className="sms-cube-edge sms-cube-inner" d="M141 86 180 107 219 86M180 107V151" />
          </g>

          <g className="sms-core">
            <circle className="sms-halo" cx="180" cy="151" r="19" />
            <circle className="sms-breath" cx="180" cy="151" r="10" />
            <circle className="sms-node" cx="180" cy="151" r="3.5" />
          </g>

          <g className="sms-markers">
            <circle className="sms-marker sms-marker-a" cx="269" cy="149" r="2.4" />
            <circle className="sms-marker sms-marker-b" cx="123" cy="173" r="2" />
            <circle className="sms-marker sms-marker-c" cx="201" cy="124" r="1.8" />
          </g>
        </g>
      </svg>
    </div>
  );
}
