from pathlib import Path
from unittest.mock import patch
import pytest
from services.desktop_agent_web_build_runner import build_web_worker_source

ARGS = dict(db='unused',staging_root='unused',output_root='unused',request_id='r',
            agent_id='a',principal_id='p',tenant_id='t')


def test_build_refuses_unapproved_environment():
    with pytest.raises(PermissionError,match='sandbox'):
        build_web_worker_source(**ARGS)


def test_build_requires_lockfile_before_running_commands(tmp_path):
    source = tmp_path/'src'
    source.mkdir()
    with patch('services.desktop_agent_web_build_runner.consume_staged_web_source',
               return_value={'source_path':str(source),'artifact_sha256':'a'*64}):
        with patch('services.desktop_agent_web_build_runner.subprocess.run') as run:
            with pytest.raises(PermissionError,match='lockfile'):
                build_web_worker_source(**ARGS,sandbox_approved=True)
            run.assert_not_called()


def test_build_evidence_binds_original_upload_and_rejects_failed_typecheck(tmp_path):
    source = tmp_path/'src'
    (source/'.next').mkdir(parents=True)
    (source/'package-lock.json').write_text('{}')
    (source/'.next'/'BUILD_ID').write_text('real-build-id')
    proof = {'source_path':str(source),'artifact_sha256':'a'*64}
    with patch('services.desktop_agent_web_build_runner.consume_staged_web_source',return_value=proof):
        with patch('services.desktop_agent_web_build_runner.subprocess.run') as run:
            run.return_value.returncode = 0
            evidence = build_web_worker_source(**ARGS,sandbox_approved=True)
            assert evidence['worker_artifact_sha256']=='a'*64
            assert evidence['typecheck_passed'] and not evidence['coordinator_accepted']
            assert run.call_count==3
            run.reset_mock()
            run.side_effect = [type('R',(),{'returncode':0})(),type('R',(),{'returncode':1})()]
            with pytest.raises(PermissionError,match='typecheck'):
                build_web_worker_source(**ARGS,sandbox_approved=True)
            assert run.call_count==2
