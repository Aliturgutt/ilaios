"""Opt-in isolated worker-source Next.js build; never promotes coordinator state.

Run only in a dedicated sandbox with network and filesystem confinement.
"""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from services.desktop_agent_web_source_consumer import consume_staged_web_source


def build_web_worker_source(db, staging_root, output_root, *, request_id,
                            agent_id, principal_id, tenant_id,
                            sandbox_approved=False, timeout_seconds=180):
    if sandbox_approved is not True:
        raise PermissionError('dedicated Web build sandbox required')
    proof = consume_staged_web_source(db, staging_root, output_root,
        request_id=request_id, agent_id=agent_id,
        principal_id=principal_id, tenant_id=tenant_id)
    source = Path(proof['source_path'])
    if not (source / 'package-lock.json').is_file():
        raise PermissionError('immutable npm lockfile required for worker build')
    # No shell invocation; npm must be installed inside the approved sandbox.
    env = {key: value for key, value in os.environ.items()
           if key.upper() not in ('NODE_OPTIONS', 'NPM_CONFIG_SCRIPT_SHELL')}
    env['NEXT_TELEMETRY_DISABLED'] = '1'
    results = []
    for command in (('npm.cmd' if os.name == 'nt' else 'npm', 'ci', '--ignore-scripts', '--offline'),
                    ('npm.cmd' if os.name == 'nt' else 'npm', 'run', 'typecheck'),
                    ('npm.cmd' if os.name == 'nt' else 'npm', 'run', 'build')):
        try:
            result = subprocess.run(command, cwd=source, env=env, shell=False,
                capture_output=True, text=True, timeout=timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PermissionError('sandbox Web build failed or timed out') from error
        if result.returncode != 0:
            raise PermissionError('sandbox Web build or typecheck failed')
        results.append({'command':list(command[1:]), 'exit_code':result.returncode})
    build = source / '.next' / 'BUILD_ID'
    if not build.is_file() or not build.read_text().strip():
        raise PermissionError('Next.js build evidence missing')
    evidence = {'worker_artifact_sha256':proof['artifact_sha256'],
        'agent_id':agent_id, 'request_id':request_id,
        'tenant_id':tenant_id, 'principal_id':principal_id,
        'build_id_sha256':hashlib.sha256(build.read_bytes()).hexdigest(),
        'steps':results, 'build_passed':True, 'typecheck_passed':True,
        'coordinator_accepted':False}
    return evidence
