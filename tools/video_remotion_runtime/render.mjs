import fs from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {bundle} from "@remotion/bundler";
import {renderMedia, selectComposition} from "@remotion/renderer";

const runtimeRoot = path.dirname(fileURLToPath(import.meta.url));
const [manifestArg, outputArg] = process.argv.slice(2);

if (!manifestArg || !outputArg || process.argv.length !== 4) {
  throw new Error("usage: node render.mjs <manifest.json> <output.mp4>");
}

const manifestPath = path.resolve(manifestArg);
const outputPath = path.resolve(outputArg);
const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));

if (!manifest || manifest.schema_version !== 1 || manifest.engine !== "remotion") {
  throw new Error("unsupported ILAIOS Remotion manifest");
}
if (!manifest.composition || !Array.isArray(manifest.elements) || !Array.isArray(manifest.timeline)) {
  throw new Error("invalid ILAIOS Remotion manifest structure");
}
for (const key of ["duration_frames", "fps", "width", "height"]) {
  const value = manifest.composition[key];
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`invalid composition field: ${key}`);
  }
}

await fs.mkdir(path.dirname(outputPath), {recursive: true});
const serveUrl = await bundle({
  entryPoint: path.join(runtimeRoot, "src", "index.tsx"),
});
const inputProps = {manifest};
const composition = await selectComposition({
  serveUrl,
  id: "ILAIOSVideo",
  inputProps,
});

await renderMedia({
  composition,
  serveUrl,
  codec: "h264",
  outputLocation: outputPath,
  inputProps,
  pixelFormat: "yuv420p",
  overwrite: true,
});

const stat = await fs.stat(outputPath);
if (!stat.isFile() || stat.size <= 0) {
  throw new Error("Remotion renderer did not create a non-empty MP4");
}
