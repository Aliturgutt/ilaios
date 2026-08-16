from __future__ import annotations

import gc
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_software_runtime
from services.execution_coordinator import ExecutionCoordinator
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DeterministicLocalVideoRuntime,
    DurableVideoProductRuntime,
    RecoverableSoftwareProductRuntime,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    source_head = _git_head(repo_root)
    artifact_root_raw = os.environ.get("ILAIOS_SOFTWARE_E2E_ARTIFACT_DIR", "").strip()
    artifact_root = None if not artifact_root_raw else Path(artifact_root_raw).resolve()
    temporary = Path(tempfile.mkdtemp(prefix="ilaios-software-e2e-"))
    try:
        _run_finished_product_acceptance(
            root=temporary,
            source_head=source_head,
            artifact_root=artifact_root,
        )
    finally:
        gc.collect()
        for attempt in range(5):
            try:
                shutil.rmtree(temporary)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                gc.collect()
                time.sleep(0.25 * (attempt + 1))
    return 0


def _run_finished_product_acceptance(
    *,
    root: Path,
    source_head: str,
    artifact_root: Path | None,
) -> None:
    local_credential = "ci-local-boundary"
    database = root / "control-plane.sqlite3"
    control_plane = ControlPlane(ControlPlaneConfig(database, local_credential))
    workflows = WorkflowStore(WorkflowStoreConfig(database))
    scheduler = DurableWorkerScheduler(
        database,
        lease_duration=timedelta(seconds=30),
    )
    grants = DurableGrantPolicy(database)
    evidence = EvidenceStore(root / "evidence")
    governance = GovernedRuntimeGateway(
        root / "governance.sqlite3",
        GovernedRuntime(database),
        hard_cap_minor=100,
    )

    video = DeterministicLocalVideoRuntime(
        root / "video",
        grants,
        governance,
        evidence,
    )
    video_product = DurableVideoProductRuntime(
        root / "video-product.sqlite3",
        control_plane,
        workflows,
        scheduler,
        grants,
        governance,
        video,
    )
    software_product = RecoverableSoftwareProductRuntime(
        root / "software-product.sqlite3",
        control_plane,
        workflows,
        scheduler,
        grants,
        governance,
        evidence,
        root / "software",
        source_head_sha=source_head,
    )
    coordinator = ExecutionCoordinator(
        root / "execution-coordinator.sqlite3",
        control_plane,
        governance,
        grants,
        video_product,
        evidence,
    )
    register_software_runtime(coordinator, software_product)

    request_id = "desktop-software-task-manager-e2e"
    objective = "Build me a simple production-quality task manager software application"
    now = datetime.now(timezone.utc)
    prepared = coordinator.prepare(
        request_id,
        objective,
        token=local_credential,
        principal_id="ci-desktop-software-user",
        tenant_id="ci-desktop-tenant",
        now=now,
    )
    if prepared.get("execution_status") != "ADMITTED":
        raise RuntimeError(f"software request was not admitted: {prepared}")
    if prepared.get("adapter_id") != "software.product-runtime.v1":
        raise RuntimeError(f"wrong software adapter: {prepared}")

    manifest = coordinator.resume(
        request_id,
        token=local_credential,
        now=now + timedelta(seconds=1),
    )
    if manifest.get("accepted") is not True:
        raise RuntimeError(f"Software AcceptanceManifest did not pass: {manifest}")
    if manifest.get("final_disposition") != "ACCEPT":
        raise RuntimeError("Software final disposition is not ACCEPT")
    if manifest.get("source_head_sha") != source_head:
        raise RuntimeError("Software artifact provenance is not bound to exact CI HEAD")
    if manifest.get("external_provider_cost_minor") != 0:
        raise RuntimeError("Software acceptance unexpectedly used paid provider capacity")
    if manifest.get("commercial_release_pass") is not False:
        raise RuntimeError("Software fixture must not imply whole-product commercial release")

    coordinator_state = coordinator.get(request_id)
    if coordinator_state.get("execution_status") != "ACCEPTED":
        raise RuntimeError(f"coordinator did not reach ACCEPTED: {coordinator_state}")

    digest = manifest.get("artifact_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise RuntimeError("Software AcceptanceManifest is missing artifact SHA-256")
    content = evidence.get_artifact(digest)
    if hashlib.sha256(content).hexdigest() != digest:
        raise RuntimeError("EvidenceStore delivery digest mismatch")
    with zipfile.ZipFile(io.BytesIO(content), "r") as archive:
        names = sorted(archive.namelist())
        if names != ["README.txt", "app.js", "index.html", "styles.css"]:
            raise RuntimeError(f"unexpected finished-product ZIP inventory: {names}")
        if b"Task Manager" not in archive.read("index.html"):
            raise RuntimeError("finished software UI is missing")
        if b"localStorage" not in archive.read("app.js"):
            raise RuntimeError("finished software persistence behavior is missing")

    for key in ("security_result", "test_result", "build_result", "runtime_result"):
        value = manifest.get(key)
        if not isinstance(value, dict) or value.get("passed") is not True:
            raise RuntimeError(f"Software acceptance stage did not pass: {key}={value}")

    runtime_result = cast(dict[str, object], manifest["runtime_result"])
    if runtime_result.get("external_network_used") is not False:
        raise RuntimeError("Software runtime QA used external network")
    if runtime_result.get("browser_javascript_execution_proven") is not False:
        raise RuntimeError("Software runtime truth boundary is malformed")

    persisted_artifact: str | None = None
    if artifact_root is not None:
        output = artifact_root / source_head
        output.mkdir(parents=True, exist_ok=True)
        artifact_path = output / "finished-software.zip"
        artifact_path.write_bytes(content)
        if hashlib.sha256(artifact_path.read_bytes()).hexdigest() != digest:
            raise RuntimeError("persisted Software artifact digest mismatch")
        persisted_artifact = str(artifact_path)
        evidence_payload = {
            "request_id": request_id,
            "source_head_sha": source_head,
            "adapter_id": manifest["adapter_id"],
            "factory": manifest["factory"],
            "accepted": manifest["accepted"],
            "final_disposition": manifest["final_disposition"],
            "artifact_sha256": digest,
            "artifact_size": len(content),
            "generated_files": manifest["generated_files"],
            "provenance_record_hash": manifest["provenance_record_hash"],
            "external_provider_cost_minor": manifest["external_provider_cost_minor"],
            "security_result": manifest["security_result"],
            "test_result": manifest["test_result"],
            "build_result": manifest["build_result"],
            "runtime_result": manifest["runtime_result"],
            "coordinator_result_sha256": coordinator_state["result_sha256"],
            "closure_status": coordinator_state["execution_status"],
        }
        (output / "evidence.json").write_text(
            json.dumps(evidence_payload, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "acceptance_manifest": "PASS",
                "adapter_id": manifest["adapter_id"],
                "artifact_sha256": digest,
                "artifact_path": persisted_artifact,
                "external_provider_cost_minor": 0,
                "generated_files": manifest["generated_files"],
                "runtime_qa": "PASS",
                "security": "PASS",
                "source_head_sha": source_head,
            },
            sort_keys=True,
        )
    )
    print("ILAIOS_DESKTOP_SOFTWARE_FINISHED_PRODUCT_E2E=PASS")


def _git_head(repository: Path) -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    value = completed.stdout.strip()
    if completed.returncode != 0 or len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise RuntimeError("exact source HEAD is unavailable for Software acceptance")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
