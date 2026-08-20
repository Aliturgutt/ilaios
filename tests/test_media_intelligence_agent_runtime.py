import sqlite3
from pathlib import Path

from services.control_plane.migrations import migrate_database
from services.media_intelligence_agent_runtime import (
    compose_media_intelligence_agent_runtime,
)
from services.p0_runtime_composition import compose_p0_runtime
from services.runtime import GovernedRuntime, GrantPolicy
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters
from services.software_factory_skills import default_skills_root
from services.web_agent_runtime import compose_web_agent_runtime

ROOT = Path(__file__).resolve().parents[1]


def _runtime(tmp_path: Path) -> tuple[Path, GovernedRuntime]:
    database = tmp_path / "state.sqlite3"
    migrate_database(database)
    security = SecurityAgentRuntimeAdapters()
    return database, GovernedRuntime(
        database,
        external_adapters=security.runtime_adapters(),
    )


def test_p0_and_all_p1_identities_share_one_runtime_without_ai(tmp_path: Path) -> None:
    database, runtime = _runtime(tmp_path)
    p0 = compose_p0_runtime(
        runtime,
        GrantPolicy(),
        engineering_skills_root=default_skills_root(ROOT),
    )
    web = compose_web_agent_runtime(p0.named_executor, ROOT)
    with sqlite3.connect(database) as connection:
        baseline_skill_count = connection.execute(
            "SELECT COUNT(*) FROM runtime_skills"
        ).fetchone()[0]

    media_intelligence = compose_media_intelligence_agent_runtime(
        p0.named_executor,
        ROOT,
    )

    assert p0.target_agent_count == 21
    assert web.target_agent_count == 6
    assert media_intelligence.target_agent_count == 12
    assert web.ai_configured is False
    assert media_intelligence.ai_configured is False
    assert media_intelligence.direct_network_authority is False
    assert media_intelligence.direct_media_side_effect_authority is False
    assert media_intelligence.direct_publish_authority is False

    with sqlite3.connect(database) as connection:
        agent_count = connection.execute(
            "SELECT COUNT(*) FROM runtime_agents"
        ).fetchone()[0]
        skill_count = connection.execute(
            "SELECT COUNT(*) FROM runtime_skills"
        ).fetchone()[0]
        provider_count = connection.execute(
            "SELECT COUNT(*) FROM runtime_providers"
        ).fetchone()[0]
    assert agent_count == 40
    assert skill_count == baseline_skill_count + media_intelligence.skill_count
    assert provider_count == 6


def test_p1_composition_is_restart_idempotent_on_same_runtime(tmp_path: Path) -> None:
    database, runtime = _runtime(tmp_path)
    p0 = compose_p0_runtime(
        runtime,
        GrantPolicy(),
        engineering_skills_root=default_skills_root(ROOT),
    )
    compose_web_agent_runtime(p0.named_executor, ROOT)
    with sqlite3.connect(database) as connection:
        baseline_skill_count = connection.execute(
            "SELECT COUNT(*) FROM runtime_skills"
        ).fetchone()[0]

    first = compose_media_intelligence_agent_runtime(p0.named_executor, ROOT)
    second = compose_media_intelligence_agent_runtime(p0.named_executor, ROOT)
    assert first.target_agent_count == second.target_agent_count == 12
    assert first.skill_count == second.skill_count == 15
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM runtime_agents"
        ).fetchone()[0] == 40
        assert connection.execute(
            "SELECT COUNT(*) FROM runtime_skills"
        ).fetchone()[0] == baseline_skill_count + first.skill_count
        assert connection.execute(
            "SELECT COUNT(*) FROM runtime_providers"
        ).fetchone()[0] == 6
