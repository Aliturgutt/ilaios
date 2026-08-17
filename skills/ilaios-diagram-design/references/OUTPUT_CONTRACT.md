# Output Contract

## Native outputs

### SVG

A valid native SVG must:

- be standalone;
- start with `<svg>`;
- include `xmlns`;
- include a fixed width/height and `viewBox`;
- include `role="img"`;
- include `aria-labelledby`;
- include an SVG `<title>` and `<desc>`;
- contain no network-loaded resources;
- contain no executable script.

The spec hash prefixes SVG IDs so multiple generated diagrams can coexist without common marker/title ID collisions.

### HTML

HTML is only a dependency-free presentation wrapper around an already validated native SVG. It must not introduce:
- JavaScript;
- CDN styles;
- remote fonts;
- remote images;
- analytics;
- iframe content.

### Evidence JSON

Evidence must contain:

```json
{
  "artifact_sha256": "<64 hex>",
  "spec_sha256": "<64 hex>",
  "checks": [
    "standalone-svg",
    "accessible-title-desc",
    "no-script-or-foreign-object",
    "no-gradients-filters-or-external-assets",
    "ilaios-flat-vector-policy"
  ]
}
```

## Determinism

`spec_sha256` is calculated from a canonical JSON representation including:
- title/description;
- kind;
- ordered nodes and edges;
- dimensions/direction;
- dark-mode flag;
- semantic theme tokens.

`artifact_sha256` is calculated from the exact emitted SVG bytes.

The same renderer version and same canonical spec must produce the same hashes.

## Accessibility

SVG title and description must explain the artifact without requiring color perception. Edge semantics remain in the underlying `DiagramSpec`; color is supplemental.

## File naming

Recommended:

```text
<slug>.svg
<slug>.html
<slug>.evidence.json
```

Do not overwrite unrelated files. The calling governed workflow owns output destination and retention.
