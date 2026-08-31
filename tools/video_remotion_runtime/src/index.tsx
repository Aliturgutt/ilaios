import React from "react";
import {
  AbsoluteFill,
  Composition,
  Sequence,
  interpolate,
  registerRoot,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

type ElementPayload = Record<string, string>;

type ManifestElement = {
  element_id: string;
  kind: string;
  start_frame: number;
  duration_frames: number;
  layer: number;
  payload: ElementPayload;
};

type Manifest = {
  schema_version: number;
  engine: string;
  job_id: string;
  composition: {
    duration_frames: number;
    fps: number;
    width: number;
    height: number;
  };
  elements: ManifestElement[];
};

type VideoProps = {manifest: Manifest};

const textFor = (element: ManifestElement): string =>
  element.payload.text ?? element.payload.title ?? element.payload.label ?? element.kind;

const Element = ({element}: {element: ManifestElement}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const opacity = interpolate(frame, [0, Math.max(1, Math.round(fps * 0.3))], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rise = interpolate(frame, [0, Math.max(1, Math.round(fps * 0.35))], [24, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const common: React.CSSProperties = {
    color: "#FFFFFF",
    fontFamily: "Arial, sans-serif",
    opacity,
    transform: `translateY(${rise}px)`,
  };

  if (element.kind === "progress_indicator") {
    const progress = Math.min(1, frame / Math.max(1, element.duration_frames - 1));
    return (
      <div style={{position: "absolute", left: 64, right: 64, bottom: 64, height: 10, background: "#1F2937"}}>
        <div style={{height: "100%", width: `${progress * 100}%`, background: "#00C2D1"}} />
      </div>
    );
  }

  if (element.kind === "chart") {
    const raw = Number(element.payload.value ?? "65");
    const value = Number.isFinite(raw) ? Math.max(0, Math.min(100, raw)) : 65;
    const progress = interpolate(frame, [0, Math.max(1, Math.round(fps * 0.6))], [0, value], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <div style={{position: "absolute", left: 96, right: 96, bottom: 120}}>
        <div style={{...common, fontSize: 36, marginBottom: 18}}>{textFor(element)}</div>
        <div style={{height: 48, background: "#1F2937"}}>
          <div style={{height: "100%", width: `${progress}%`, background: "#00C2D1"}} />
        </div>
      </div>
    );
  }

  const lower = element.kind === "lower_third" || element.kind === "dynamic_caption";
  return (
    <div
      style={{
        ...common,
        position: "absolute",
        left: lower ? 72 : 96,
        right: lower ? 72 : 96,
        bottom: lower ? 88 : undefined,
        top: lower ? undefined : "32%",
        fontSize: lower ? 42 : 64,
        fontWeight: 700,
        lineHeight: 1.08,
        padding: lower ? "18px 24px" : 0,
        background: lower ? "#1F2937" : "transparent",
      }}
    >
      {textFor(element)}
    </div>
  );
};

const ILAIOSVideo = ({manifest}: VideoProps) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const motion = (frame / Math.max(1, durationInFrames - 1)) * 100;
  return (
    <AbsoluteFill style={{background: "#0B0F14", overflow: "hidden"}}>
      <div style={{position: "absolute", top: 0, left: 0, height: 8, width: `${motion}%`, background: "#00C2D1"}} />
      {manifest.elements
        .slice()
        .sort((a, b) => a.layer - b.layer || a.start_frame - b.start_frame || a.element_id.localeCompare(b.element_id))
        .map((element) => (
          <Sequence key={element.element_id} from={element.start_frame} durationInFrames={element.duration_frames} layout="none">
            <Element element={element} />
          </Sequence>
        ))}
    </AbsoluteFill>
  );
};

const Root = () => (
  <Composition
    id="ILAIOSVideo"
    component={ILAIOSVideo}
    durationInFrames={1}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={{
      manifest: {
        schema_version: 1,
        engine: "remotion",
        job_id: "default",
        composition: {duration_frames: 1, fps: 30, width: 1920, height: 1080},
        elements: [],
      },
    }}
    calculateMetadata={({props}) => ({
      durationInFrames: props.manifest.composition.duration_frames,
      fps: props.manifest.composition.fps,
      width: props.manifest.composition.width,
      height: props.manifest.composition.height,
    })}
  />
);

registerRoot(Root);
