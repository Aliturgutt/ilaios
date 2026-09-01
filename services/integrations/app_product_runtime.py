"""Bounded Windows-first Flutter finished-product runtime for App Factory.

This composes the existing App Factory and canonical execution stack. Generated
source lives only under the configured artifact root. Signing, Store submission,
production deployment, paid providers, and arbitrary-app claims remain outside
this adapter's authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from services.app_factory import AppFactory
from services.control_plane import BudgetEnvelope, ControlPlane, DataClass, ProposedTask, RiskClass
from services.governance import GovernedRuntimeGateway
from services.runtime import DurableGrantPolicy
from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import (
    FlutterRuntimeAdapter,
    RuntimeCommand,
    SecureCommandBoundary,
    evidence_json,
)
from src.video_automation.models import JobState

from .product_runtime import ProductFinalizationPending

_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WINDOWS_TERMS = (
    "windows app",
    "windows desktop app",
    "desktop app",
    "masaustu uygulama",
    "masaüstü uygulama",
)
_BOUNDED_PRODUCT_TERMS = (
    "task",
    "todo",
    "checklist",
    "görev",
    "gorev",
    "yapılacak",
    "yapilacak",
)


class AppProductRuntimeError(RuntimeError):
    """A bounded App finished product could not be proven."""


class AppProductFinalizationPending(ProductFinalizationPending):
    """Durable App acceptance is finalizing and must be reconciled."""


@dataclass(frozen=True, slots=True)
class WindowsAppBuildEvidence:
    platform: str
    scope: str
    artifact_path: str
    artifact_sha256: str
    artifact_size: int
    source_sha256: str
    runtime_adapter_id: str
    runtime_workspace_sha256: str
    runtime_evidence_sha256: str
    scaffold_stdout_sha256: str
    scaffold_stderr_sha256: str
    generated_files: tuple[str, ...]
    exe_name: str
    signed: bool
    store_submitted: bool
    passed: bool


class WindowsFlutterAppExecutor:
    """Generate and verify one bounded task/checklist Flutter app on Windows."""

    scope = "BOUNDED_LOCAL_TASK_CHECKLIST_WINDOWS_APP"
    _project_name = "ilaios_generated_app"

    def __init__(self, root: Path, boundary: SecureCommandBoundary) -> None:
        self._root = root.resolve()
        self._boundary = boundary
        self._root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def supports(objective: str) -> bool:
        normalized = " ".join(objective.casefold().split())
        return any(term in normalized for term in _WINDOWS_TERMS) and any(
            term in normalized for term in _BOUNDED_PRODUCT_TERMS
        )

    def build(self, request_id: str, objective: str) -> WindowsAppBuildEvidence:
        if _REQUEST_ID.fullmatch(request_id) is None:
            raise AppProductRuntimeError("app request_id is not a bounded identifier")
        if not self.supports(objective):
            raise AppProductRuntimeError(
                "requested app is outside the verified Windows task/checklist scope"
            )
        run_root = (self._root / request_id).resolve()
        if self._root != run_root and self._root not in run_root.parents:
            raise AppProductRuntimeError("app workspace escaped its artifact root")
        if run_root.exists():
            raise AppProductRuntimeError("app build workspace already exists")
        project = run_root / "project"
        project.mkdir(parents=True)
        policy = ExecutionPolicy(
            frozenset({"project"}),
            network_allowed=False,
            secrets_allowed=False,
            secure_mode=True,
            max_files=10_000,
            max_bytes=500_000_000,
            timeout_seconds=900,
        )
        scaffold = self._boundary.execute(
            run_root,
            RuntimeCommand(
                "scaffold",
                (
                    "flutter",
                    "create",
                    "--no-pub",
                    "--platforms=windows",
                    "--project-name",
                    self._project_name,
                    ".",
                ),
                "project",
            ),
            policy,
        )
        if not scaffold.passed:
            raise AppProductRuntimeError("Flutter Windows scaffold failed")
        self._write_first_party_source(project, objective)
        package_command = (
            "pwsh",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "$ErrorActionPreference='Stop';"
            "$release='build\\windows\\x64\\runner\\Release';"
            "$exe=Join-Path $release 'ilaios_generated_app.exe';"
            "if(-not(Test-Path $exe)){throw 'generated Windows executable missing'};"
            "$dest='build\\ilaios_generated_app_windows.zip';"
            "if(Test-Path $dest){Remove-Item $dest -Force};"
            "Compress-Archive -Path (Join-Path $release '*') -DestinationPath $dest -Force",
        )
        adapter = FlutterRuntimeAdapter(
            self._boundary,
            root_hint="project",
            build_mode="release",
            package_command=package_command,
        )
        try:
            results = (
                adapter.prepare(run_root, policy),
                adapter.resolve_dependencies(run_root, policy),
                adapter.lint(run_root, policy),
                adapter.typecheck(run_root, policy),
                adapter.test(run_root, policy),
                adapter.build(run_root, policy),
                adapter.package(run_root, policy),
                adapter.smoke_test(run_root, policy),
            )
            runtime_evidence = adapter.collect_evidence(run_root, results)
        except SoftwareFactoryError as error:
            raise AppProductRuntimeError(str(error)) from error
        if not runtime_evidence.passed:
            raise AppProductRuntimeError("Flutter Windows runtime lifecycle failed")
        artifact = project / "build" / "ilaios_generated_app_windows.zip"
        executable = (
            project
            / "build"
            / "windows"
            / "x64"
            / "runner"
            / "Release"
            / "ilaios_generated_app.exe"
        )
        if not artifact.is_file() or artifact.stat().st_size <= 0:
            raise AppProductRuntimeError("generated Windows package is missing")
        if not executable.is_file() or executable.stat().st_size <= 0:
            raise AppProductRuntimeError("generated Windows executable is missing")
        generated_files = (
            "pubspec.yaml",
            "analysis_options.yaml",
            "lib/main.dart",
            "test/widget_test.dart",
        )
        source_sha = _selected_source_digest(project, generated_files)
        runtime_json = evidence_json(runtime_evidence)
        return WindowsAppBuildEvidence(
            platform="windows",
            scope=self.scope,
            artifact_path=artifact.relative_to(self._root).as_posix(),
            artifact_sha256=_file_sha256(artifact),
            artifact_size=artifact.stat().st_size,
            source_sha256=source_sha,
            runtime_adapter_id=runtime_evidence.adapter_id,
            runtime_workspace_sha256=runtime_evidence.workspace_sha256,
            runtime_evidence_sha256=hashlib.sha256(runtime_json.encode()).hexdigest(),
            scaffold_stdout_sha256=scaffold.stdout_sha256,
            scaffold_stderr_sha256=scaffold.stderr_sha256,
            generated_files=generated_files,
            exe_name=executable.name,
            signed=False,
            store_submitted=False,
            passed=True,
        )

    def _write_first_party_source(self, project: Path, objective: str) -> None:
        objective_literal = json.dumps(" ".join(objective.split())[:320], ensure_ascii=False)
        pubspec = """name: ilaios_generated_app
description: ILAIOS bounded generated Windows finished product
publish_to: 'none'
version: 1.0.0+1
environment:
  sdk: '>=3.8.0 <4.0.0'
dependencies:
  flutter:
    sdk: flutter
dev_dependencies:
  flutter_test:
    sdk: flutter
flutter:
  uses-material-design: true
"""
        analysis = """analyzer:
  exclude:
    - build/**
"""
        main = f'''import 'package:flutter/material.dart';

const generatedObjective = {objective_literal};

void main() => runApp(const GeneratedApp());

class GeneratedApp extends StatelessWidget {{
  const GeneratedApp({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'ILAIOS Generated App',
      home: const TaskWorkspace(),
    );
  }}
}}

class TaskWorkspace extends StatefulWidget {{
  const TaskWorkspace({{super.key}});

  @override
  State<TaskWorkspace> createState() => _TaskWorkspaceState();
}}

class _TaskWorkspaceState extends State<TaskWorkspace> {{
  final TextEditingController _controller = TextEditingController();
  final List<({{String text, bool done}})> _tasks = [];

  void _addTask() {{
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    setState(() {{
      _tasks.insert(0, (text: text, done: false));
      _controller.clear();
    }});
  }}

  @override
  void dispose() {{
    _controller.dispose();
    super.dispose();
  }}

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(title: const Text('ILAIOS Task Workspace')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text('Generated objective', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                Text(generatedObjective),
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _controller,
                        decoration: const InputDecoration(
                          labelText: 'New task',
                          border: OutlineInputBorder(),
                        ),
                        onSubmitted: (_) => _addTask(),
                      ),
                    ),
                    const SizedBox(width: 12),
                    FilledButton(onPressed: _addTask, child: const Text('Add task')),
                  ],
                ),
                const SizedBox(height: 18),
                Expanded(
                  child: _tasks.isEmpty
                      ? const Center(child: Text('No tasks yet'))
                      : ListView.builder(
                          itemCount: _tasks.length,
                          itemBuilder: (context, index) {{
                            final task = _tasks[index];
                            return ListTile(
                              leading: Checkbox(
                                value: task.done,
                                onChanged: (value) => setState(() {{
                                  _tasks[index] = (text: task.text, done: value ?? false);
                                }}),
                              ),
                              title: Text(
                                task.text,
                                style: TextStyle(
                                  decoration: task.done ? TextDecoration.lineThrough : null,
                                ),
                              ),
                              trailing: IconButton(
                                tooltip: 'Delete task',
                                icon: const Icon(Icons.delete_outline),
                                onPressed: () => setState(() => _tasks.removeAt(index)),
                              ),
                            );
                          }},
                        ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }}
}}
'''
        test = """import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_generated_app/main.dart';

void main() {
  testWidgets('generated task workspace supports the primary flow', (tester) async {
    await tester.pumpWidget(const GeneratedApp());
    expect(find.text('ILAIOS Task Workspace'), findsOneWidget);
    expect(find.text('Add task'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'Ship release');
    await tester.tap(find.text('Add task'));
    await tester.pump();
    expect(find.text('Ship release'), findsOneWidget);
  });
}
"""
        (project / "pubspec.yaml").write_text(pubspec, encoding="utf-8", newline="\n")
        (project / "analysis_options.yaml").write_text(
            analysis, encoding="utf-8", newline="\n"
        )
        lib = project / "lib"
        tests = project / "test"
        lib.mkdir(exist_ok=True)
        tests.mkdir(exist_ok=True)
        (lib / "main.dart").write_text(main, encoding="utf-8", newline="\n")
        (tests / "widget_test.dart").write_text(test, encoding="utf-8", newline="\n")


class DurableAppProductRuntime:
    """Durable App adapter over the bounded Windows Flutter executor."""

    adapter_id = "app.product-runtime.windows.v1"

    def __init__(
        self,
        database_path: Path,
        control_plane: ControlPlane,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        artifact_root: Path,
        executor: WindowsFlutterAppExecutor,
        *,
        source_head_sha: str,
    ) -> None:
        if _SHA1.fullmatch(source_head_sha) is None:
            raise ValueError("source_head_sha must be an exact lowercase SHA-1")
        self._database_path = database_path
        self._control_plane = control_plane
        self._grants = grants
        self._governance = governance
        self._artifact_root = artifact_root.resolve()
        self._executor = executor
        self._source_head_sha = source_head_sha
        self._factory = AppFactory()
        self._artifact_root.mkdir(parents=True, exist_ok=True)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS app_product_requests ("
                "request_id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, job_id TEXT NOT NULL, "
                "proposal_id TEXT NOT NULL, principal_id TEXT NOT NULL, tenant_id TEXT NOT NULL, "
                "objective TEXT NOT NULL, app_request_id TEXT NOT NULL, app_request_sha256 TEXT NOT NULL, "
                "status TEXT NOT NULL, manifest_json TEXT)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS app_product_closure ("
                "request_id TEXT PRIMARY KEY, terminal_status TEXT NOT NULL, "
                "reason TEXT NOT NULL, terminal_at TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def supports(self, objective: str) -> bool:
        return self._executor.supports(objective)

    def prepare(
        self,
        request_id: str,
        objective: str,
        *,
        token: str,
        now: datetime,
        requester_id: str,
        tenant_id: str,
        risk: str = "medium",
        data_class: DataClass = DataClass.INTERNAL,
        budget: BudgetEnvelope = BudgetEnvelope(1, 900, 0),
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise AppProductRuntimeError("app execution time must be timezone-aware")
        if not self.supports(objective):
            raise AppProductRuntimeError(
                "requested app is outside the verified Windows task/checklist scope"
            )
        try:
            risk_class = RiskClass(risk)
        except ValueError as error:
            raise AppProductRuntimeError("unsupported app risk classification") from error
        if data_class is not DataClass.INTERNAL:
            raise AppProductRuntimeError("verified App runtime accepts INTERNAL data only")
        if budget.max_external_spend_minor != 0:
            raise AppProductRuntimeError("verified App runtime is local/free only")
        app_request = self._factory.propose(
            f"runtime-{request_id}",
            platform="windows",
            action="build_plan",
            objective=objective,
            target_path=f"artifacts/app/windows/{request_id}.json",
        )
        goal = self._control_plane.create_goal(token, objective)
        job = self._control_plane.create_job(token, goal.goal_id)
        proposal = self._control_plane.create_proposal(
            token,
            goal.goal_id,
            acceptance_criteria=(
                "App Factory request fingerprint is bound to the execution",
                "First-party Flutter source passes format/analyze/test",
                "Real Windows release build produces a non-empty executable",
                "Unsigned Windows package and AcceptanceManifest are content addressed",
                "Signing and Store submission remain outside adapter authority",
            ),
            risk_class=risk_class,
            data_class=data_class,
            budget=budget,
            tasks=(
                ProposedTask("app-build", "Build governed Windows Flutter application"),
                ProposedTask(
                    "app-validate",
                    "Validate Windows package and acceptance evidence",
                    ("app-build",),
                ),
            ),
        )
        proposal_id = str(proposal["proposal_id"])
        admission = self._governance.submit(
            request_id,
            requester_id,
            "app-agent",
            "app-factory-windows-finished-product-v1",
            "app",
            {
                "goal_id": goal.goal_id,
                "job_id": job.job_id,
                "tenant_id": tenant_id,
                "platform": "windows",
                "app_request_sha256": app_request.request_sha256,
                "provider_policy": "LOCAL_FREE_ONLY",
            },
            (),
            risk=risk,
        )
        decision = str(admission.get("admission_decision", ""))
        human = bool(admission.get("human_approval_required", False))
        if decision not in {"ALLOW", "REQUIRE_APPROVAL"}:
            raise AppProductRuntimeError("app admission was denied or malformed")
        if (decision == "ALLOW" and human) or (
            decision == "REQUIRE_APPROVAL" and not human
        ):
            raise AppProductRuntimeError("app admission approval state is inconsistent")
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO app_product_requests VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL)",
                    (
                        request_id,
                        goal.goal_id,
                        job.job_id,
                        proposal_id,
                        requester_id,
                        tenant_id,
                        objective,
                        app_request.request_id,
                        app_request.request_sha256,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise AppProductRuntimeError("app product request already exists") from error
        return {
            "request_id": request_id,
            "requester_id": requester_id,
            "tenant_id": tenant_id,
            "goal_id": goal.goal_id,
            "job_id": job.job_id,
            "proposal_id": proposal_id,
            "adapter_id": self.adapter_id,
            "platform": "windows",
            "app_request_sha256": app_request.request_sha256,
            "admission_decision": decision,
            "human_approval_required": human,
            "status": "pending_approval" if human else "admitted_pending_grant",
        }

    def execute(
        self,
        request_id: str,
        grant_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise AppProductRuntimeError("app execution time must be timezone-aware")
        row = self._pending(request_id)
        try:
            admission = self._governance.admission_snapshot(request_id)
            if admission["admission_proven"] is not True:
                raise AppProductRuntimeError("governed app admission is not proven")
            job_id = str(row["job_id"])
            self._control_plane.transition_job(
                token,
                job_id,
                JobState.RUNNING,
                reason="governed App Factory Windows finished-product build started",
                now=now,
            )
            self._grants.authorize_and_record(
                grant_id,
                subject_id="worker-app",
                action="app.build",
                resource=job_id,
                now=now,
            )
            build = self._executor.build(request_id, str(row["objective"]))
            if not _build_is_acceptable(build):
                raise AppProductRuntimeError("Windows Flutter build evidence is incomplete")
            self._control_plane.transition_job(
                token,
                job_id,
                JobState.VALIDATING,
                reason="Windows Flutter package built; validating acceptance evidence",
                now=now,
            )
            grant_rows = cast(list[dict[str, object]], self._grants.state()["grants"])
            grant_proven = any(
                item["grant_id"] == grant_id and item["used_side_effects"] == 1
                for item in grant_rows
            )
            if not grant_proven:
                raise AppProductRuntimeError("app execution grant proof is missing")
            manifest: dict[str, object] = {
                "manifest_version": "1.0",
                "adapter_id": self.adapter_id,
                "factory": "ilaios.capability.app-factory",
                "request_id": request_id,
                "requester_id": row["principal_id"],
                "tenant_id": row["tenant_id"],
                "identity_proven": bool(row["principal_id"]) and bool(row["tenant_id"]),
                "goal_id": row["goal_id"],
                "job_id": job_id,
                "proposal_id": row["proposal_id"],
                "app_request_id": row["app_request_id"],
                "app_request_sha256": row["app_request_sha256"],
                "base_sha": self._source_head_sha,
                "source_head_sha": self._source_head_sha,
                "platform": build.platform,
                "verification_scope": build.scope,
                "generated_files": list(build.generated_files),
                "generated_source_sha256": build.source_sha256,
                "runtime_adapter_id": build.runtime_adapter_id,
                "runtime_workspace_sha256": build.runtime_workspace_sha256,
                "runtime_evidence_sha256": build.runtime_evidence_sha256,
                "artifact_path": build.artifact_path,
                "artifact_sha256": build.artifact_sha256,
                "artifact_size": build.artifact_size,
                "executable_name": build.exe_name,
                "grant_id": grant_id,
                "grant_proven": True,
                "admission_decision": admission["admission_decision"],
                "human_approval_required": admission["human_approval_required"],
                "approval_proven": admission["approval_proven"],
                "admission_proven": admission["admission_proven"],
                "provider_mode": "LOCAL_FREE_ONLY",
                "external_provider_cost_minor": 0,
                "signed": build.signed,
                "store_submitted": build.store_submitted,
                "deployment_state": "NOT_DEPLOYED",
                "commercial_release_pass": False,
                "job_state_proven": False,
                "finalization_status": "finalizing",
                "accepted": False,
            }
            serialized = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                changed = connection.execute(
                    "UPDATE app_product_requests SET status='finalizing', manifest_json=? "
                    "WHERE request_id=? AND status='pending'",
                    (serialized, request_id),
                ).rowcount
            if changed != 1:
                raise AppProductRuntimeError(
                    "app product finalization state changed concurrently"
                )
            try:
                return self.recover_finalizing(request_id, token=token, now=now)
            except Exception as error:
                raise AppProductFinalizationPending(
                    "app product acceptance is durably finalizing and requires recovery"
                ) from error
        except AppProductFinalizationPending:
            raise
        except Exception as error:
            self._fail(row, token=token, now=now, error=error)
            raise

    def recover_finalizing(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise AppProductRuntimeError("app finalization time must be timezone-aware")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, job_id, manifest_json FROM app_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise AppProductRuntimeError("unknown app product request")
        if row["status"] == "accepted":
            return self.get_manifest(request_id)
        if row["status"] != "finalizing" or row["manifest_json"] is None:
            raise AppProductRuntimeError("app product is not finalizing")
        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise AppProductRuntimeError("stored App AcceptanceManifest is malformed")
        manifest = cast(dict[str, object], value)
        if not _manifest_is_finalizable(manifest, request_id, str(row["job_id"])):
            raise AppProductRuntimeError("stored App acceptance evidence is incomplete")
        job_id = str(row["job_id"])
        current = self._control_plane.get_job(token, job_id)
        if current.state is JobState.VALIDATING:
            current = self._control_plane.transition_job(
                token,
                job_id,
                JobState.COMPLETED,
                reason="durable App Windows package acceptance evidence verified",
                now=now,
            )
        if current.state is not JobState.COMPLETED:
            raise AppProductRuntimeError("finalizing App job is not completable")
        manifest["job_state_proven"] = True
        manifest["finalization_status"] = "accepted"
        manifest["accepted"] = True
        serialized = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current_row = connection.execute(
                "SELECT status, manifest_json FROM app_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if current_row is None:
                raise AppProductRuntimeError("unknown app product request")
            if current_row["status"] == "accepted":
                stored = current_row["manifest_json"]
                if stored is None:
                    raise AppProductRuntimeError("accepted App manifest is missing")
                accepted = json.loads(str(stored))
                if not isinstance(accepted, dict):
                    raise AppProductRuntimeError("stored App manifest is malformed")
                return cast(dict[str, object], accepted)
            if current_row["status"] != "finalizing":
                raise AppProductRuntimeError(
                    "app product finalization state changed concurrently"
                )
            changed = connection.execute(
                "UPDATE app_product_requests SET status='accepted', manifest_json=? "
                "WHERE request_id=? AND status='finalizing'",
                (serialized, request_id),
            ).rowcount
            if changed != 1:
                raise AppProductRuntimeError(
                    "app product finalization state changed concurrently"
                )
            connection.execute(
                "INSERT OR IGNORE INTO app_product_closure VALUES (?, 'accepted', ?, ?)",
                (
                    request_id,
                    "Windows Flutter source, executable, package and AcceptanceManifest verified",
                    now.isoformat(),
                ),
            )
        return manifest

    def get_manifest(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, manifest_json FROM app_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None or row["status"] != "accepted" or row["manifest_json"] is None:
            raise AppProductRuntimeError("accepted app product is unavailable")
        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise AppProductRuntimeError("stored app AcceptanceManifest is malformed")
        return cast(dict[str, object], value)

    def get_state(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT principal_id, tenant_id, status FROM app_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            closure = connection.execute(
                "SELECT terminal_status, reason, terminal_at FROM app_product_closure WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise AppProductRuntimeError("unknown app product request")
        return {
            "request_id": request_id,
            "requester_id": str(row["principal_id"]),
            "tenant_id": str(row["tenant_id"]),
            "status": str(row["status"]),
            "terminal": closure is not None,
            "terminal_status": None if closure is None else str(closure["terminal_status"]),
            "reason": None if closure is None else str(closure["reason"]),
            "terminal_at": None if closure is None else str(closure["terminal_at"]),
        }

    def interrupt(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
        reason: str,
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise AppProductRuntimeError("interruption time must be timezone-aware")
        normalized = " ".join(reason.split())
        if not normalized:
            raise AppProductRuntimeError("interruption reason is required")
        state = self.get_state(request_id)
        if state["status"] == "accepted":
            return state
        if state["status"] == "finalizing":
            self.recover_finalizing(request_id, token=token, now=now)
            return self.get_state(request_id)
        if state["status"] in {"failed", "interrupted", "cancelled"}:
            return state
        with self._connect() as connection:
            row = connection.execute(
                "SELECT job_id FROM app_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise AppProductRuntimeError("unknown app product request")
        current = self._control_plane.get_job(token, str(row["job_id"]))
        if current.state not in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
            self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.CANCELLED,
                reason="finished App product execution interrupted",
                now=now,
            )
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE app_product_requests SET status='interrupted' "
                "WHERE request_id=? AND status='pending'",
                (request_id,),
            ).rowcount
            if changed == 1:
                connection.execute(
                    "INSERT OR IGNORE INTO app_product_closure VALUES (?, 'interrupted', ?, ?)",
                    (request_id, normalized, now.isoformat()),
                )
        return self.get_state(request_id)

    def _pending(self, request_id: str) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM app_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None or row["status"] != "pending":
            raise AppProductRuntimeError("app product request is not pending")
        return cast(sqlite3.Row, row)

    def _fail(
        self,
        row: sqlite3.Row,
        *,
        token: str,
        now: datetime,
        error: Exception,
    ) -> None:
        request_id = str(row["request_id"])
        reason = _failure_reason(error)
        try:
            current = self._control_plane.get_job(token, str(row["job_id"]))
            if current.state is JobState.PENDING:
                self._control_plane.transition_job(
                    token,
                    str(row["job_id"]),
                    JobState.CANCELLED,
                    reason="App finished-product execution failed before start",
                    now=now,
                )
            elif current.state in {
                JobState.RUNNING,
                JobState.WAITING_PROVIDER,
                JobState.VALIDATING,
                JobState.RETRY_PENDING,
            }:
                self._control_plane.transition_job(
                    token,
                    str(row["job_id"]),
                    JobState.FAILED,
                    reason="App finished-product execution failed closed",
                    now=now,
                )
        except Exception as cleanup_error:
            reason = f"{reason}; cleanup_failure={type(cleanup_error).__name__}"[:2048]
        with self._connect() as connection:
            connection.execute(
                "UPDATE app_product_requests SET status='failed' "
                "WHERE request_id=? AND status='pending'",
                (request_id,),
            )
            connection.execute(
                "INSERT OR IGNORE INTO app_product_closure VALUES (?, 'failed', ?, ?)",
                (request_id, reason, now.isoformat()),
            )


def _build_is_acceptable(build: WindowsAppBuildEvidence) -> bool:
    return all(
        (
            build.passed,
            build.platform == "windows",
            build.scope == WindowsFlutterAppExecutor.scope,
            build.runtime_adapter_id == "ilaios.runtime.flutter",
            len(build.artifact_sha256) == 64,
            len(build.source_sha256) == 64,
            len(build.runtime_workspace_sha256) == 64,
            len(build.runtime_evidence_sha256) == 64,
            build.artifact_size > 0,
            bool(build.generated_files),
            build.exe_name == "ilaios_generated_app.exe",
            build.signed is False,
            build.store_submitted is False,
        )
    )


def _manifest_is_finalizable(
    manifest: dict[str, object], request_id: str, job_id: str
) -> bool:
    return all(
        (
            manifest.get("adapter_id") == DurableAppProductRuntime.adapter_id,
            manifest.get("request_id") == request_id,
            manifest.get("job_id") == job_id,
            manifest.get("identity_proven") is True,
            manifest.get("admission_proven") is True,
            manifest.get("grant_proven") is True,
            manifest.get("platform") == "windows",
            manifest.get("verification_scope") == WindowsFlutterAppExecutor.scope,
            bool(manifest.get("generated_source_sha256")),
            bool(manifest.get("runtime_evidence_sha256")),
            bool(manifest.get("artifact_sha256")),
            manifest.get("signed") is False,
            manifest.get("store_submitted") is False,
            manifest.get("deployment_state") == "NOT_DEPLOYED",
            manifest.get("commercial_release_pass") is False,
            manifest.get("finalization_status") == "finalizing",
            manifest.get("accepted") is False,
        )
    )


def _selected_source_digest(project: Path, names: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for name in sorted(names):
        path = project / name
        if not path.is_file():
            raise AppProductRuntimeError(f"generated source file is missing: {name}")
        digest.update(name.encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_evidence_json(evidence: WindowsAppBuildEvidence) -> str:
    return json.dumps(asdict(evidence), sort_keys=True, separators=(",", ":"))


def _failure_reason(error: Exception) -> str:
    message = " ".join(str(error).split())
    if not message:
        message = "App execution failed without an error message"
    return f"{type(error).__name__}: {message}"[:2048]


__all__ = [
    "AppProductFinalizationPending",
    "AppProductRuntimeError",
    "DurableAppProductRuntime",
    "WindowsAppBuildEvidence",
    "WindowsFlutterAppExecutor",
    "build_evidence_json",
]
