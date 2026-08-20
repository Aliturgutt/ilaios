from __future__ import annotations

from pathlib import Path

WEB_FACTORY = Path("services/integrations/web_factory.py")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one marker, found {count}")
    return source.replace(old, new, 1)


def main() -> None:
    source = WEB_FACTORY.read_text(encoding="utf-8")

    source = replace_once(
        source,
        "from services.runtime import ExecutionGrant, GrantPolicy\n",
        "from services.runtime import ExecutionGrant, GrantPolicy\n"
        "from services.web_3d_integration import integrate_web_3d_into_generated_content\n"
        "from services.web_3d_runtime import compile_web_3d_runtime_plan\n",
        "3D imports",
    )

    source = replace_once(
        source,
        "_REQUIRED_VIEWPORTS = (320, 360, 390, 412, 430, 768, 1024, 1440)\n",
        "_REQUIRED_VIEWPORTS = (320, 360, 390, 412, 430, 768, 1024, 1440)\n"
        "_WEB3D_FEATURES = frozenset(\n"
        "    {\n"
        "        \"3d-hero\",\n"
        "        \"scroll-camera\",\n"
        "        \"product-rotation\",\n"
        "        \"parallax\",\n"
        "        \"particles\",\n"
        "        \"webgl-background\",\n"
        "        \"3d-typography\",\n"
        "        \"pointer-interaction\",\n"
        "    }\n"
        ")\n"
        "_EXPLICIT_3D_TERMS = (\n"
        "    \"3d\",\n"
        "    \"webgl\",\n"
        "    \"webgpu\",\n"
        "    \"three-dimensional\",\n"
        "    \"three dimensional\",\n"
        "    \"üç boyutlu\",\n"
        "    \"uc boyutlu\",\n"
        ")\n",
        "3D constants",
    )

    source = replace_once(
        source,
        "        content = _generated_site_content(spec, strategy)\n"
        "        artifact_hash = _content_hash(content)\n",
        "        content = _generated_site_content(spec, strategy)\n"
        "        web3d_features = _requested_web3d_features(spec.features)\n"
        "        web3d_evidence: dict[str, object] | None = None\n"
        "        if web3d_features:\n"
        "            plan = compile_web_3d_runtime_plan(_web3d_instruction(web3d_features))\n"
        "            integrated = integrate_web_3d_into_generated_content(\n"
        "                content,\n"
        "                plan,\n"
        "                home_routes=tuple(f\"{locale}/index.html\" for locale in spec.locales),\n"
        "            )\n"
        "            content = integrated.content\n"
        "            web3d_evidence = {\n"
        "                \"status\": \"SOURCE_INTEGRATED_NOT_BROWSER_CERTIFIED\",\n"
        "                \"features\": web3d_features,\n"
        "                \"plan_sha256\": integrated.plan_sha256,\n"
        "                \"runtime_source_sha256\": integrated.runtime_source_sha256,\n"
        "                \"runtime_path\": integrated.runtime_path,\n"
        "                \"bundle_sha256\": integrated.bundle_sha256,\n"
        "            }\n"
        "        artifact_hash = _content_hash(content)\n",
        "generated-site 3D composition",
    )

    source = replace_once(
        source,
        "        qa = _validate_generated_site(bundle, spec, strategy, routes, files)\n"
        "        spec_hash = hashlib.sha256(\n",
        "        qa = _validate_generated_site(bundle, spec, strategy, routes, files)\n"
        "        if web3d_evidence is not None:\n"
        "            qa[\"web3d\"] = web3d_evidence\n"
        "        spec_hash = hashlib.sha256(\n",
        "3D acceptance evidence",
    )

    old_features = '''def _features(normalized: str, pages: tuple[str, ...]) -> tuple[str, ...]:
    features: list[str] = []
    if "contact" in pages:
        features.append("contact-form")
    if any(term in normalized for term in ("blog", "articles", "makale")):
        features.append("content")
    if any(term in normalized for term in ("newsletter", "bülten")):
        features.append("newsletter")
    if any(term in normalized for term in ("search", "arama")):
        features.append("search")
    return tuple(features)
'''
    new_features = '''def _features(normalized: str, pages: tuple[str, ...]) -> tuple[str, ...]:
    features: list[str] = []
    if "contact" in pages:
        features.append("contact-form")
    if any(term in normalized for term in ("blog", "articles", "makale")):
        features.append("content")
    if any(term in normalized for term in ("newsletter", "bülten")):
        features.append("newsletter")
    if any(term in normalized for term in ("search", "arama")):
        features.append("search")
    if any(term in normalized for term in _EXPLICIT_3D_TERMS):
        selected: list[str] = []
        if any(term in normalized for term in ("hero", "landing", "launch", "tanıtım", "tanitim")):
            selected.append("3d-hero")
        if any(term in normalized for term in ("scroll", "camera", "kamera", "scroll-driven", "scroll driven")):
            selected.append("scroll-camera")
        if any(term in normalized for term in ("rotate", "rotation", "product model", "model rotation", "döndür", "dondur")):
            selected.append("product-rotation")
        if any(term in normalized for term in ("parallax", "paralaks")):
            selected.append("parallax")
        if any(term in normalized for term in ("particle", "particles", "parçacık", "parcacik")):
            selected.append("particles")
        if any(term in normalized for term in ("webgl background", "3d background", "3d arka plan")):
            selected.append("webgl-background")
        if any(term in normalized for term in ("3d typography", "3d text", "3d tipografi")):
            selected.append("3d-typography")
        if any(term in normalized for term in ("interactive", "mouse", "pointer", "touch", "etkileşim", "etkilesim")):
            selected.append("pointer-interaction")
        if not selected:
            selected.append("3d-hero")
        features.extend(selected)
    return tuple(features)


def _requested_web3d_features(features: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(feature for feature in features if feature in _WEB3D_FEATURES)


def _web3d_instruction(features: tuple[str, ...]) -> str:
    phrases = {
        "3d-hero": "3D hero",
        "scroll-camera": "scroll camera motion",
        "product-rotation": "interactive product model rotation",
        "parallax": "parallax",
        "particles": "particles",
        "webgl-background": "WebGL background",
        "3d-typography": "3D typography",
        "pointer-interaction": "interactive mouse pointer touch control",
    }
    requested = [phrases[feature] for feature in features]
    return "Build a website with 3D WebGL: " + ", ".join(requested) + "."
'''
    source = replace_once(source, old_features, new_features, "3D feature derivation")

    source = replace_once(
        source,
        "    expected = {*routes, \"assets/site.css\", \"robots.txt\", \"sitemap.xml\"}\n"
        "    actual = {\n",
        "    expected = {*routes, \"assets/site.css\", \"robots.txt\", \"sitemap.xml\"}\n"
        "    web3d_features = _requested_web3d_features(spec.features)\n"
        "    if web3d_features:\n"
        "        expected.add(\"assets/3d/index.html\")\n"
        "    actual = {\n",
        "3D artifact set validation",
    )

    source = replace_once(
        source,
        "    if \"@media (prefers-reduced-motion:reduce)\" not in css or \":focus-visible\" not in css:\n"
        "        raise ValueError(\"generated website accessibility behavior is incomplete\")\n"
        "    return {\n",
        "    if \"@media (prefers-reduced-motion:reduce)\" not in css or \":focus-visible\" not in css:\n"
        "        raise ValueError(\"generated website accessibility behavior is incomplete\")\n"
        "    if web3d_features:\n"
        "        for locale in spec.locales:\n"
        "            home = (bundle / locale / \"index.html\").read_text(encoding=\"utf-8\")\n"
        "            if (\n"
        "                'class=\"ilaios-web3d-frame\"' not in home\n"
        "                or 'sandbox=\"allow-scripts\"' not in home\n"
        "                or 'referrerpolicy=\"no-referrer\"' not in home\n"
        "            ):\n"
        "                raise ValueError(\"generated website 3D integration boundary is incomplete\")\n"
        "        runtime = (bundle / \"assets/3d/index.html\").read_text(encoding=\"utf-8\")\n"
        "        required_runtime_fragments = (\n"
        "            \"getContext('webgl2'\",\n"
        "            \"getContext('webgl'\",\n"
        "            \"prefers-reduced-motion: reduce\",\n"
        "            \"requestAnimationFrame\",\n"
        "            \"data-fallback\",\n"
        "        )\n"
        "        if any(fragment not in runtime for fragment in required_runtime_fragments):\n"
        "            raise ValueError(\"generated website 3D runtime validation failed\")\n"
        "        if \"https://\" in runtime or \"<script src=\" in runtime or \"eval(\" in runtime:\n"
        "            raise ValueError(\"generated website 3D runtime contains forbidden external authority\")\n"
        "    return {\n",
        "3D runtime structural validation",
    )

    WEB_FACTORY.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
