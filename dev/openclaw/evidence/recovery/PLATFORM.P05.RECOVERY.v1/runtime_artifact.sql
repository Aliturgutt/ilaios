BEGIN TRANSACTION;
CREATE TABLE events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            schema_version TEXT NOT NULL
        );
INSERT INTO "events" VALUES(1,'goal.created','goal-00000001','{"objective": "P05 runtime recovery evidence"}','2026-08-09T13:19:13.273154+00:00','1.0');
INSERT INTO "events" VALUES(2,'job.created','job-00000001','{"goal_id": "goal-00000001", "state": "PENDING"}','2026-08-09T13:19:13.284376+00:00','1.0');
CREATE TABLE goals (
            goal_id TEXT PRIMARY KEY,
            objective TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
INSERT INTO "goals" VALUES('goal-00000001','P05 runtime recovery evidence','2026-08-09T13:19:13.273154+00:00');
CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL REFERENCES goals(goal_id),
            state TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
INSERT INTO "jobs" VALUES('job-00000001','goal-00000001','PENDING','2026-08-09T13:19:13.284376+00:00');
CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
INSERT INTO "schema_migrations" VALUES(1,'2026-08-09 13:19:13');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('events',2);
COMMIT;
