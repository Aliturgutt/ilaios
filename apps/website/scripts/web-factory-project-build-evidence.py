#!/usr/bin/env python3
"""Compile a generated ILAIOS Web Factory Next.js project with locked repo tooling."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from services.design_quality import DesignContext, NativeDesignStrategyEngine
from services.integrations.web_factory import derive_website_spec
from services.integrations.web_project import materialize_next_project


def _strategy() -> dict[str, object]:
    strategy = NativeDesignStrategyEngine().plan(
        DesignContext(
            business_category="law firm",
            audience="corporate and enterprise decision makers",
            primary_goal="present a credible finished website aligned to the user objective",
            conversion_objective="contact or primary call-to-action conversion",
            brand_personality=("premium", "confident", "clear"),
            content_volume="medium",
            product_complexity="medium",
            trust_requirement="high",
            visual_asset_availability="standard",
            information_density="medium",
            locale="en",
        )
    )
    return {
        "primary_composition": strategy.primary_composition,
        "secondary_compositions": strategy.secondary_compositions,
        "type_behavior": strategy.type_behavior,
        "spacing_behavior": strategy.spacing_behavior,
        "surface_behavior": strategy.surface_behavior,
        "imagery_behavior": strategy.imagery_behavior,
        "cta_hierarchy": strategy.cta_hierarchy,
        "diagram_usage": strategy.diagram_usage,
        "motion_intensity": strategy.motion_intensity,
        "navigation_behavior": strategy.navigation_behavior,
        "mobile_transformation": strategy.mobile_transformation,
    }


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-8000:],
        "stderr_tail": completed.stderr[-8000:],
    }


def main() -> int:
    repository = Path.cwd().resolve()
    node_modules = (repository / "apps" / "website" / "node_modules").resolve()
    if not node_modules.is_dir():
        raise SystemExit("apps/website/node_modules is required for generated-project certification")

    output_root = repository / "artifacts" / "web-factory-project-build"
    output_root.mkdir(parents=True, exist_ok=True)
    spec = derive_website_spec(
        "web-next-build-certification",
        "Build a premium bilingual Turkish/English website for a corporate law firm",
    )
    artifact = materialize_next_project(spec, _strategy(), output_root / "projects")
    project = Path(artifact.root_path).resolve()
    link = project / "node_modules"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(node_modules, target_is_directory=True)

    env = dict(os.environ)
    env["NEXT_TELEMETRY_DISABLED"] = "1"
    tsc = node_modules / ".bin" / "tsc"
    next_bin = node_modules / ".bin" / "next"
    checks = [
        _run([str(tsc), "--noEmit", "-p", str(project / "tsconfig.json")], cwd=repository, env=env),
        _run([str(next_bin), "build", str(project)], cwd=repository, env=env),
    ]
    status = "PASS" if all(check["returncode"] == 0 for check in checks) else "FAIL"
    summary = {
        "status": status,
        "project_id": artifact.project_id,
        "source_project_digest": artifact.digest,
        "source_file_count": len(artifact.files),
        "checks": checks,
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "checks"}, sort_keys=True))
    if status != "PASS":
        for check in checks:
            if check["returncode"] != 0:
                print(check["stdout_tail"])
                print(check["stderr_tail"])
        raise SystemExit("generated Next.js project build certification failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
