# Resiliency Rules

1. Enumerate component failures, dependency failures and correlated failures.
2. Bound retries by count, elapsed time and budget; use jitter where appropriate.
3. Circuit breaking and degradation policies require recovery/re-entry conditions.
4. Define blast radius by tenant, region/failure domain and dependency.
5. Checkpoint durable workflows so crashes do not silently restart completed work.
6. Policy/security denial must fail closed and must not be repaired around.
