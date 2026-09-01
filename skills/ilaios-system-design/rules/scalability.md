# Scalability Rules

1. Scale from measurable workload units: RPS, concurrency, queue rate, payload size,
   read/write mix and storage growth.
2. A registered-user count is never a capacity proof.
3. Separate average demand from peak demand and record the peak-factor assumption.
4. Size instances only from measured sustainable per-instance throughput at a stated
   target utilization.
5. Preserve headroom for burst, retry, failover and maintenance traffic.
6. Prefer stateless horizontal scaling for request-serving compute when the workload
   permits it.
7. Treat provider quotas and downstream limits as part of end-to-end capacity.
8. Do not promote a heuristic estimate to `VERIFIED` without load-test evidence.
