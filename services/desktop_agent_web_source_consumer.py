"""Isolated consumption and static QA of staged, authenticated Web source.

Does not replace canonical Web factory build, grant, or coordinator acceptance.
"""
import hashlib
import json
import zipfile
from pathlib import Path
from services.desktop_agent_web_staging import stage_web_worker_upload

_REQUIRED = frozenset(('package.json', 'app/layout.tsx', 'app/page.tsx'))


def consume_staged_web_source(db, staging_root, output_root, *, request_id,
                              agent_id, principal_id, tenant_id):
    proof = stage_web_worker_upload(db, staging_root, request_id=request_id,
        agent_id=agent_id, principal_id=principal_id, tenant_id=tenant_id)
    target = Path(output_root) / proof['artifact_sha256']
    with zipfile.ZipFile(proof['staged_path']) as archive:
        entries = {item.filename: item for item in archive.infolist() if not item.is_dir()}
        if not _REQUIRED <= entries.keys():
            raise PermissionError('Web source missing mandatory Next.js files')
        package = json.loads(archive.read('package.json'))
        if (not isinstance(package, dict) or package.get('scripts', {}).get('build') != 'next build'
                or not isinstance(package.get('dependencies'), dict)
                or 'next' not in package['dependencies']):
            raise PermissionError('Web source lacks canonical build contract')
        files = {name: archive.read(item) for name, item in entries.items()}
    target.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        destination = target / name
        if destination.exists():
            if hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(content).digest():
                raise PermissionError('recovered Web source differs from original upload')
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
    # A source-consumption receipt, NOT a successful executable build or QA.
    return {**proof, 'source_path':str(target), 'source_files':len(files),
            'source_consumed':True, 'build_passed':False,
            'qa_passed':False, 'coordinator_accepted':False}
