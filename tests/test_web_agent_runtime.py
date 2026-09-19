import sqlite3
from pathlib import Path

from services.control_plane.migrations import migrate_database
from services.p0_runtime_composition import compose_p0_runtime
from services.runtime import GovernedRuntime, GrantPolicy
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters
from services.software_factory_skills import default_skills_root
from services.web_agent_runtime import compose_web_agent_runtime
from services.web_agent_skill_catalog import WEB_FIRST_PARTY_AGENT_SKILLS
from services.web_factory_skills import WEB_FACTORY_BROWSER_SKILL_IDS

ROOT = Path(__file__).resolve().parents[1]


def _runtime(tmp_path: Path) -> tuple[Path, GovernedRuntime]:
    database = tmp_path / "state.sqlite3"
    migrate_database(database)
    security = SecurityAgentRuntimeAdapters()
    return database, GovernedRuntime(
        database,
        external_adapters=security.runtime_adapters(),
    )


def _expected_web_skill_count() -> int:
    return len(WEB_FIRST_PARTY_AGENT_SKILLS) + len(WEB_FACTORY_BROWSER_SKILL_IDS)


def test_web_composition_reuses_p0_named_executor_and_runtime(tmp_path: Path) -> None:
    database, runtime = _runtime(tmp_path)
    p0 = compose_p0_runtime(
        runtime,
        GrantPolicy(),
        engineering_skills_root=default_skills_root(ROOT),
    )
    with sqlite3.connect(database) as connection:
        baseline_skill_count = connection.execute(
            "SELECT COUNT(*) FROM runtime_skills"
        ).fetchone()[0]

    web = compose_web_agent_runtime(p0.named_executor, ROOT)

    assert web.named_executor is p0.named_executor
    assert web.target_agent_count == 6
    assert web.provisioned_identity_count == 6
    assert web.skill_count == _expected_web_skill_count()
    assert web.browser_tool_required is True
    assert web.ai_configured is False

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

    # P0 provisions 21 identities plus IndependentVerifier; Web adds six.
    assert agent_count == 28
    assert skill_count == baseline_skill_count + _expected_web_skill_count()
    assert provider_count == 6


def test_web_composition_is_restart_idempotent_on_same_runtime(tmp_path: Path) -> None:
    database, runtime = _runtime(tmp_path)
    p0 = compose_p0_runtime(
        runtime,
        GrantPolicy(),
        engineering_skills_root=default_skills_root(ROOT),
    )
    with sqlite3.connect(database) as connection:
        baseline_skill_count = connection.execute(
            "SELECT COUNT(*) FROM runtime_skills"
        ).fetchone()[0]

    first = compose_web_agent_runtime(p0.named_executor, ROOT)
    second = compose_web_agent_runtime(p0.named_executor, ROOT)

    assert first.target_agent_count == second.target_agent_count == 6
    assert first.skill_count == second.skill_count == _expected_web_skill_count()
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM runtime_agents").fetchone()[0] == 28
        assert connection.execute("SELECT COUNT(*) FROM runtime_skills").fetchone()[0] == (
            baseline_skill_count + _expected_web_skill_count()
        )
        assert connection.execute("SELECT COUNT(*) FROM runtime_providers").fetchone()[0] == 6
