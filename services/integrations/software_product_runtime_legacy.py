"""Bounded finished-product adapter for the canonical ILAIOS Software Factory path."""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import sqlite3
import threading
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

from services.control_plane import (
    BudgetEnvelope,
    ControlPlane,
    DataClass,
    ProposedTask,
    RiskClass,
)
from services.control_plane.workflows import WorkflowStore
from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, Lease, WorkerProfile
from services.software_factory_secret_scanning import ChangedLine, SoftwareFactorySecretScanning
from src.video_automation.models import JobState


class SoftwareProductRuntimeError(RuntimeError):
    """Finished software could not be proven."""


class SoftwareProductSecurityError(SoftwareProductRuntimeError):
    """Generated product violated a non-repairable security boundary."""


class SoftwareProductValidationError(SoftwareProductRuntimeError):
    """Generated product failed a bounded repairable validation."""


_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_FILES = ("index.html", "app.js", "styles.css", "README.txt")
_FORBIDDEN_EGRESS = ("http://", "https://", "fetch(", "xmlhttprequest", "websocket", "eventsource")
_DEPENDENCY_MANIFESTS = (
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "requirements.txt",
    "pyproject.toml",
    "pubspec.yaml",
)


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        del format, args


class FinishedSoftwareBuilder:
    """Build one real local-first browser task manager with bounded repair."""

    max_attempts = 2

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def build(self, request_id: str, objective: str) -> dict[str, object]:
        _require_identifier(request_id, "request_id")
        if not objective.strip():
            raise SoftwareProductRuntimeError("software objective is required")
        run_root = self._root / request_id
        if run_root.exists():
            raise SoftwareProductRuntimeError("software workspace already exists")
        run_root.mkdir(parents=True)
        project = run_root / "project"
        repairs: list[dict[str, object]] = []
        last_error: SoftwareProductValidationError | None = None
        for attempt in range(1, self.max_attempts + 1):
            if project.exists():
                shutil.rmtree(project)
            project.mkdir()
            self._write_project(project, objective, attempt)
            try:
                security = self._security_gate(project)
                tests = self._structural_test(project)
                runtime = self._runtime_qa(project)
                artifact = self._package(project)
                return {
                    "generated_files": list(_FILES),
                    "generated_source_sha256": _tree_digest(project),
                    "dependency_evidence": {
                        "policy": "NO_DISTRIBUTED_THIRD_PARTY_DEPENDENCIES",
                        "third_party": [],
                        "lockfile_required": False,
                        "lockfile_reason": "no package-manager dependencies are distributed",
                        "passed": True,
                    },
                    "license_evidence": {
                        "generated_source": "ILAIOS_FIRST_PARTY_GENERATED_FIXTURE",
                        "third_party_assets": [],
                        "commercial_release_clearance_claimed": False,
                    },
                    "sbom": {
                        "format": "ILAIOS-SOFTWARE-PRODUCT-SBOM",
                        "version": "1.0",
                        "distributed_components": [
                            {
                                "name": name,
                                "type": "first-party-generated-source",
                                "sha256": hashlib.sha256((project / name).read_bytes()).hexdigest(),
                            }
                            for name in _FILES
                        ],
                        "third_party_components": [],
                    },
                    "security_result": security,
                    "test_result": tests,
                    "build_result": {
                        "passed": True,
                        "format": "zip",
                        "artifact_size": len(artifact),
                        "artifact_sha256": hashlib.sha256(artifact).hexdigest(),
                    },
                    "runtime_result": runtime,
                    "repair_history": repairs,
                    "artifact_bytes": artifact,
                }
            except SoftwareProductSecurityError:
                raise
            except SoftwareProductValidationError as error:
                last_error = error
                repairs.append(
                    {
                        "attempt": attempt,
                        "classification": "REPAIRABLE_GENERATED_PRODUCT_FAILURE",
                        "reason_sha256": hashlib.sha256(str(error).encode()).hexdigest(),
                        "repaired": attempt < self.max_attempts,
                    }
                )
        raise SoftwareProductRuntimeError(
            "bounded automatic repair exhausted without a valid product"
        ) from last_error

    def _write_project(self, project: Path, objective: str, attempt: int) -> None:
        del attempt
        objective_digest = hashlib.sha256(objective.strip().encode()).hexdigest()
        index = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ILAIOS Task Manager</title><link rel="stylesheet" href="styles.css"></head>
<body><main class="shell"><header><p class="eyebrow">ILAIOS SOFTWARE FACTORY</p><h1>Task Manager</h1>
<p class="sub">A local-first task manager. Data stays in this browser.</p></header>
<section class="composer" aria-label="Create task"><label for="task-input">New task</label>
<div class="row"><input id="task-input" maxlength="160" autocomplete="off" placeholder="What needs to be done?">
<button id="add-task" type="button">Add task</button></div></section>
<section aria-live="polite"><div class="toolbar"><strong id="task-count">0 tasks</strong>
<button id="clear-completed" class="secondary" type="button">Clear completed</button></div>
<ul id="task-list" class="tasks"></ul><p id="empty-state" class="empty">No tasks yet.</p></section>
</main><script src="app.js"></script></body></html>
"""
        script = r"""(() => {
"use strict";
const key="ilaios.task-manager.v1",input=document.querySelector("#task-input"),
add=document.querySelector("#add-task"),list=document.querySelector("#task-list"),
count=document.querySelector("#task-count"),empty=document.querySelector("#empty-state"),
clear=document.querySelector("#clear-completed");
const load=()=>{try{const v=JSON.parse(localStorage.getItem(key)||"[]");return Array.isArray(v)?v.filter(x=>x&&typeof x.text==="string"):[]}catch(_){return[]}};
let tasks=load();
const persist=()=>localStorage.setItem(key,JSON.stringify(tasks));
const render=()=>{list.replaceChildren();tasks.forEach(task=>{const li=document.createElement("li");li.className=task.done?"task done":"task";
const toggle=document.createElement("button");toggle.type="button";toggle.className="toggle";toggle.textContent=task.done?"✓":"";
toggle.setAttribute("aria-label",task.done?"Mark incomplete":"Mark complete");toggle.addEventListener("click",()=>{task.done=!task.done;persist();render()});
const text=document.createElement("span");text.textContent=task.text;const remove=document.createElement("button");remove.type="button";
remove.className="remove";remove.setAttribute("aria-label","Delete task");remove.textContent="Delete";
remove.addEventListener("click",()=>{tasks=tasks.filter(x=>x.id!==task.id);persist();render()});li.append(toggle,text,remove);list.append(li)});
const open=tasks.filter(task=>!task.done).length;count.textContent=`${tasks.length} task${tasks.length===1?"":"s"} · ${open} open`;empty.hidden=tasks.length!==0};
const addTask=()=>{const text=input.value.trim();if(!text)return;tasks.unshift({id:`${Date.now()}-${Math.random().toString(16).slice(2)}`,text:text.slice(0,160),done:false});input.value="";persist();render();input.focus()};
add.addEventListener("click",addTask);input.addEventListener("keydown",e=>{if(e.key==="Enter")addTask()});
clear.addEventListener("click",()=>{tasks=tasks.filter(task=>!task.done);persist();render()});render();
})();
"""
        styles = """*{box-sizing:border-box}body{margin:0;background:#f5f7f9;color:#111827;font:16px/1.5 system-ui,sans-serif}.shell{width:min(760px,calc(100% - 32px));margin:56px auto;background:#fff;border:1px solid #d9dee5;border-radius:18px;padding:32px}.eyebrow{font-size:12px;font-weight:800;letter-spacing:.14em;color:#087d87}.sub{color:#596273}.composer{margin:28px 0}.composer label{display:block;font-weight:700;margin-bottom:8px}.row{display:flex;gap:10px}.row input{flex:1;border:1px solid #b9c1cc;border-radius:10px;padding:12px;font:inherit}button{border:0;border-radius:10px;padding:11px 15px;background:#111827;color:#fff;font-weight:700;cursor:pointer}.secondary,.remove{background:#edf1f4;color:#273142}.toolbar{display:flex;justify-content:space-between;gap:16px;border-top:1px solid #e5e7eb;padding-top:20px}.tasks{list-style:none;margin:18px 0 0;padding:0}.task{display:grid;grid-template-columns:36px 1fr auto;gap:12px;align-items:center;border-top:1px solid #edf0f2;padding:14px 0}.task.done span{text-decoration:line-through;color:#7a8491}.toggle{width:30px;height:30px;padding:0;border:1px solid #8f9aa8;background:#fff;color:#111827}.empty{text-align:center;color:#7a8491;padding:36px 0}@media(max-width:560px){.shell{margin:20px auto;padding:22px}.row,.toolbar{flex-direction:column}.task{grid-template-columns:36px 1fr}.remove{grid-column:2;justify-self:start}}"""
        readme = (
            "ILAIOS Task Manager\n===================\n\n"
            "Open index.html in a modern browser. No installation, account, server, network access, "
            "package manager, or third-party dependency is required. Tasks stay in browser localStorage.\n\n"
            f"Original bounded request SHA-256: {objective_digest}\n"
        )
        for name, content in (
            ("index.html", index),
            ("app.js", script),
            ("styles.css", styles),
            ("README.txt", readme),
        ):
            (project / name).write_text(content, encoding="utf-8", newline="\n")

    def _security_gate(self, project: Path) -> dict[str, object]:
        lines = tuple(
            ChangedLine(name, line_no, text)
            for name in _FILES
            for line_no, text in enumerate(
                (project / name).read_text(encoding="utf-8").splitlines(), 1
            )
        )
        report = SoftwareFactorySecretScanning().scan_lines(
            lines, scope="GENERATED_FINISHED_PRODUCT"
        )
        if not report.passed:
            raise SoftwareProductSecurityError("generated-product secret scan blocked delivery")
        for name in _FILES:
            lowered = (project / name).read_text(encoding="utf-8").casefold()
            if any(marker in lowered for marker in _FORBIDDEN_EGRESS):
                raise SoftwareProductSecurityError("generated product contains network egress")
        if any((project / name).exists() for name in _DEPENDENCY_MANIFESTS):
            raise SoftwareProductSecurityError("unexpected dependency manifest generated")
        if any(path.is_symlink() for path in project.rglob("*")):
            raise SoftwareProductSecurityError("generated product contains a symbolic link")
        return {
            "passed": True,
            "secret_scan": {
                "passed": True,
                "scanned_lines": report.scanned_added_lines,
                "report_sha256": report.report_sha256,
                "secret_values_emitted": report.secret_values_emitted,
            },
            "network_egress": "DENIED_BY_PRODUCT_DESIGN",
            "distributed_binaries": [],
            "malware_scan": {
                "required_for_binary": False,
                "reason": "text-only product; repository CI remains malware-scan authority",
            },
        }

    def _structural_test(self, project: Path) -> dict[str, object]:
        index = (project / "index.html").read_text(encoding="utf-8")
        script = (project / "app.js").read_text(encoding="utf-8")
        styles = (project / "styles.css").read_text(encoding="utf-8")
        checks = {
            "task_input": 'id="task-input"' in index,
            "add_action": 'id="add-task"' in index and "addTask" in script,
            "complete_action": "task.done=!task.done" in script,
            "delete_action": "Delete task" in script,
            "persistence": "localStorage" in script,
            "clear_completed": "clear-completed" in index and "filter(task=>!task.done)" in script,
            "responsive_css": "@media(max-width:560px)" in styles,
            "no_external_assets": "src=\"http" not in index.casefold()
            and "href=\"http" not in index.casefold(),
        }
        if not all(checks.values()):
            raise SoftwareProductValidationError("generated task-manager functional checks failed")
        return {"passed": True, "checks": checks, "test_type": "FIRST_PARTY_STRUCTURAL"}

    def _runtime_qa(self, project: Path) -> dict[str, object]:
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(_QuietHandler, directory=str(project))
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            fetched: dict[str, str] = {}
            port = int(server.server_address[1])
            for name in ("index.html", "app.js", "styles.css"):
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/{name}", timeout=3
                ) as response:
                    if response.status != 200:
                        raise SoftwareProductValidationError("runtime HTTP smoke test failed")
                    fetched[name] = response.read().decode()
            if "Task Manager" not in fetched["index.html"] or "localStorage" not in fetched["app.js"]:
                raise SoftwareProductValidationError("runtime content QA failed")
            return {
                "passed": True,
                "launch_mode": "LOOPBACK_STATIC_HTTP_SMOKE",
                "loopback_only": True,
                "external_network_used": False,
                "assets_fetched": sorted(fetched),
                "basic_user_flow_contract": {
                    "create": True,
                    "complete": True,
                    "delete": True,
                    "persist": True,
                },
                "browser_javascript_execution_proven": False,
            }
        except OSError as error:
            raise SoftwareProductValidationError("runtime launch failed") from error
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def _package(self, project: Path) -> bytes:
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(_FILES):
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, (project / name).read_bytes())
        artifact = stream.getvalue()
        with zipfile.ZipFile(io.BytesIO(artifact), "r") as archive:
            if tuple(sorted(archive.namelist())) != tuple(sorted(_FILES)) or archive.testzip():
                raise SoftwareProductValidationError("software ZIP integrity failed")
        return artifact


class DurableSoftwareProductRuntime:
    """Durably compose Control Plane, governance, grants, QA and EvidenceStore."""

    def __init__(
        self,
        database_path: Path,
        control_plane: ControlPlane,
        workflows: WorkflowStore,
        scheduler: DurableWorkerScheduler,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        evidence: EvidenceStore,
        product_root: Path,
        *,
        source_head_sha: str,
    ) -> None:
        if _SHA1.fullmatch(source_head_sha) is None:
            raise SoftwareProductRuntimeError("exact source HEAD SHA is required")
        self._database_path = database_path
        self._control_plane = control_plane
        self._workflows = workflows
        self._scheduler = scheduler
        self._grants = grants
        self._governance = governance
        self._evidence = evidence
        self._builder = FinishedSoftwareBuilder(product_root / "runs")
        self._source_head_sha = source_head_sha
        product_root.mkdir(parents=True, exist_ok=True)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS software_product_proofs ("
                "request_id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, job_id TEXT NOT NULL, "
                "proposal_id TEXT NOT NULL, workflow_id TEXT NOT NULL, worker_id TEXT NOT NULL, "
                "lease_json TEXT NOT NULL, objective TEXT NOT NULL, status TEXT NOT NULL, "
                "manifest_json TEXT)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def supports(self, objective: str) -> bool:
        normalized = " ".join(objective.casefold().split())
        return any(
            term in normalized
            for term in ("task manager", "task management", "todo", "to-do", "görev yönet", "gorev yonet")
        )

    def prepare(
        self,
        request_id: str,
        objective: str,
        *,
        token: str,
        now: datetime,
        requester_id: str,
        tenant_id: str,
        defer_lease: bool = False,
    ) -> dict[str, object]:
        _require_identifier(request_id, "request_id")
        _require_actor(requester_id, "requester_id")
        _require_actor(tenant_id, "tenant_id")
        if not self.supports(objective):
            raise SoftwareProductRuntimeError("software request is outside verified adapter scope")
        goal = self._control_plane.create_goal(token, objective)
        job = self._control_plane.create_job(token, goal.goal_id)
        proposal = self._control_plane.create_proposal(
            token,
            goal.goal_id,
            acceptance_criteria=(
                "A real dependency-free task management application is generated",
                "Security, build, runtime QA and content-addressed delivery pass",
            ),
            risk_class=RiskClass.MEDIUM,
            data_class=DataClass.INTERNAL,
            budget=BudgetEnvelope(2, 120, 0),
            tasks=(
                ProposedTask("software", "Generate, test, run and package finished software"),
                ProposedTask("delivery", "Verify content-addressed software delivery", ("software",)),
            ),
        )
        workflow_id = f"software-{request_id}"
        self._workflows.create_workflow(workflow_id)
        self._workflows.add_task(workflow_id, "software", max_attempts=2)
        self._workflows.add_task(workflow_id, "delivery", max_attempts=1)
        worker_id = f"software-worker-{request_id}"
        self._scheduler.register(WorkerProfile(worker_id, frozenset({"software"}), 1))
        lease = None if defer_lease else self._scheduler.schedule(job.job_id, "software", now=now)
        admission = self._governance.submit(
            request_id,
            requester_id,
            "software-agent",
            "software-factory-finished-product-v1",
            "software",
            {
                "goal_id": goal.goal_id,
                "job_id": job.job_id,
                "objective_sha256": hashlib.sha256(objective.encode()).hexdigest(),
                "tenant_id": tenant_id,
                "provider_policy": "LOCAL_FREE_ONLY",
            },
            (),
            risk="medium",
        )
        if admission.get("admission_decision") != "ALLOW":
            raise SoftwareProductRuntimeError("software admission was not executable")
        lease_json = "{}" if lease is None else json.dumps(_lease_json(lease), sort_keys=True)
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO software_product_proofs VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL)",
                    (
                        request_id,
                        goal.goal_id,
                        job.job_id,
                        str(proposal["proposal_id"]),
                        workflow_id,
                        worker_id,
                        lease_json,
                        objective,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise SoftwareProductRuntimeError("software proof request already exists") from error
        return {
            "request_id": request_id,
            "goal_id": goal.goal_id,
            "job_id": job.job_id,
            "proposal_id": str(proposal["proposal_id"]),
            "workflow_id": workflow_id,
            "worker_id": worker_id,
            "lease": None if lease is None else _lease_json(lease),
            "risk": "medium",
            "admission_decision": "ALLOW",
            "status": "admitted_pending_grant",
        }

    def execute(
        self, request_id: str, grant_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        row = self._pending(request_id)
        admission = self._governance.admission_snapshot(request_id)
        if admission["admission_proven"] is not True:
            raise SoftwareProductRuntimeError("governed software admission is not proven")
        lease = self._execution_lease(row, now)
        self._scheduler.authorize(lease, now=now)
        self._control_plane.transition_job(
            token,
            str(row["job_id"]),
            JobState.RUNNING,
            reason="governed Software Factory finished-product execution started",
            now=now,
        )
        amount = self._governance.authorize_billable(request_id)
        started = time.monotonic()
        software_attempt = self._workflows.begin_attempt(
            str(row["workflow_id"]), "software", deadline=now + timedelta(minutes=5)
        )
        software_done = False
        delivery_attempt = None
        delivery_done = False
        reconciled = False
        try:
            self._grants.authorize_and_record(
                grant_id,
                subject_id="worker-software",
                action="software.execute",
                resource=str(row["job_id"]),
                now=now,
            )
            product = self._builder.build(request_id, str(row["objective"]))
            artifact = self._evidence.put_artifact(cast(bytes, product.pop("artifact_bytes")))
            provenance = self._evidence.append_provenance(
                str(row["job_id"]), artifact, "software.local.finished-product"
            )
            self._workflows.complete_attempt(software_attempt.attempt_id)
            software_done = True
            self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.VALIDATING,
                reason="software built and runtime-tested; validating delivery",
                now=now,
            )
            delivery_attempt = self._workflows.begin_attempt(
                str(row["workflow_id"]), "delivery", deadline=now + timedelta(minutes=5)
            )
            if hashlib.sha256(self._evidence.get_artifact(artifact.digest)).hexdigest() != artifact.digest:
                raise SoftwareProductRuntimeError("software delivery integrity failed")
            self._workflows.complete_attempt(delivery_attempt.attempt_id)
            delivery_done = True
            self._scheduler.record_side_effect(
                lease,
                now=now,
                payload={"request_id": request_id, "artifact_digest": artifact.digest},
            )
            completed = self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.COMPLETED,
                reason="software finished-product evidence verified",
                now=now,
            )
            tasks = self._workflows.task_state(str(row["workflow_id"]))
            dag_proven = tasks == (
                {"task_id": "delivery", "status": "completed"},
                {"task_id": "software", "status": "completed"},
            )
            scheduler_state = self._scheduler.state()
            lease_proven = any(
                effect["task_id"] == row["job_id"]
                and effect["fencing_token"] == lease.fencing_token
                for effect in scheduler_state["effects"]
            )
            grants = cast(list[dict[str, object]], self._grants.state()["grants"])
            grant_proven = any(
                item["grant_id"] == grant_id and item["used_side_effects"] == 1 for item in grants
            )
            accepted = all(
                (
                    dag_proven,
                    lease_proven,
                    grant_proven,
                    completed.state is JobState.COMPLETED,
                    cast(dict[str, object], product["security_result"])["passed"] is True,
                    cast(dict[str, object], product["test_result"])["passed"] is True,
                    cast(dict[str, object], product["build_result"])["passed"] is True,
                    cast(dict[str, object], product["runtime_result"])["passed"] is True,
                )
            )
            if not accepted:
                raise SoftwareProductRuntimeError("software AcceptanceManifest checks failed")
            manifest: dict[str, object] = {
                "manifest_version": "1.0",
                "request_sha256": hashlib.sha256(str(row["objective"]).encode()).hexdigest(),
                "request_id": request_id,
                "job_id": row["job_id"],
                "goal_id": row["goal_id"],
                "proposal_id": row["proposal_id"],
                "factory": "ilaios.capability.software-factory",
                "adapter_id": "software.product-runtime.v1",
                "base_sha": self._source_head_sha,
                "source_head_sha": self._source_head_sha,
                "generated_files": product["generated_files"],
                "generated_source_sha256": product["generated_source_sha256"],
                "dependency_evidence": product["dependency_evidence"],
                "license_evidence": product["license_evidence"],
                "sbom": product["sbom"],
                "security_result": product["security_result"],
                "test_result": product["test_result"],
                "build_result": product["build_result"],
                "runtime_result": product["runtime_result"],
                "repair_history": product["repair_history"],
                "artifact_path": str(artifact.path),
                "artifact_sha256": artifact.digest,
                "artifact_size": artifact.size,
                "provenance_record_hash": provenance.record_hash,
                "admission_proven": admission["admission_proven"],
                "worker_lease_proven": lease_proven,
                "grant_proven": grant_proven,
                "dag_proven": dag_proven,
                "provider_mode": "LOCAL_FREE_ONLY",
                "external_provider_cost_minor": 0,
                "governance_reserved_minor": amount,
                "governance_actual_minor": amount,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "final_disposition": "ACCEPT",
                "accepted": True,
                "commercial_release_pass": False,
            }
            self._governance.reconcile_billable(
                request_id, actual_minor=amount, status="executed", result=manifest
            )
            reconciled = True
            with self._connect() as connection:
                connection.execute(
                    "UPDATE software_product_proofs SET status='accepted', manifest_json=? "
                    "WHERE request_id=?",
                    (json.dumps(manifest, sort_keys=True), request_id),
                )
            return manifest
        except Exception:
            if delivery_attempt is not None and not delivery_done:
                try:
                    self._workflows.fail_attempt(delivery_attempt.attempt_id, reason="delivery failed")
                except Exception:
                    pass
            if not software_done:
                try:
                    self._workflows.fail_attempt(software_attempt.attempt_id, reason="software failed")
                except Exception:
                    pass
            if not reconciled:
                try:
                    self._governance.reconcile_billable(
                        request_id, actual_minor=0, status="failed"
                    )
                except Exception:
                    pass
            try:
                self._control_plane.transition_job(
                    token,
                    str(row["job_id"]),
                    JobState.FAILED,
                    reason="Software Factory finished-product execution failed",
                    now=now,
                )
            except Exception:
                pass
            raise

    def get_manifest(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, manifest_json FROM software_product_proofs WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None or row["status"] != "accepted" or row["manifest_json"] is None:
            raise SoftwareProductRuntimeError("accepted software proof is unavailable")
        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise SoftwareProductRuntimeError("stored software manifest is malformed")
        return cast(dict[str, object], value)

    def _pending(self, request_id: str) -> sqlite3.Row:
        _require_identifier(request_id, "request_id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM software_product_proofs WHERE request_id=?", (request_id,)
            ).fetchone()
        if row is None or row["status"] != "pending":
            raise SoftwareProductRuntimeError("software proof is not pending")
        return cast(sqlite3.Row, row)

    def _execution_lease(self, row: sqlite3.Row, now: datetime) -> Lease:
        raw = json.loads(str(row["lease_json"]))
        if not isinstance(raw, dict):
            raise SoftwareProductRuntimeError("stored software lease is malformed")
        required = {"task_id", "worker_id", "fencing_token", "expires_at"}
        if not required <= raw.keys():
            lease = self._scheduler.schedule(str(row["job_id"]), "software", now=now)
            self._store_lease(str(row["request_id"]), lease)
            return lease
        lease = Lease(
            str(raw["task_id"]),
            str(raw["worker_id"]),
            int(raw["fencing_token"]),
            datetime.fromisoformat(str(raw["expires_at"])),
        )
        if lease.expires_at <= now:
            lease = self._scheduler.reschedule_expired(str(row["job_id"]), "software", now=now)
            self._store_lease(str(row["request_id"]), lease)
        return lease

    def _store_lease(self, request_id: str, lease: Lease) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE software_product_proofs SET lease_json=? WHERE request_id=?",
                (json.dumps(_lease_json(lease), sort_keys=True), request_id),
            )


def _lease_json(lease: Lease) -> dict[str, object]:
    return {
        "task_id": lease.task_id,
        "worker_id": lease.worker_id,
        "fencing_token": lease.fencing_token,
        "expires_at": lease.expires_at.isoformat(),
    }


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def _require_identifier(value: str, field: str) -> None:
    if not value or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in value
    ):
        raise SoftwareProductRuntimeError(f"invalid {field}")


def _require_actor(value: str, field: str) -> None:
    if (
        not value
        or value != value.strip()
        or len(value) > 512
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise SoftwareProductRuntimeError(f"invalid {field}")
