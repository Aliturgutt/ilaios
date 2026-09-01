# Observability Rules

1. Define SLIs that directly measure the stated latency, availability and correctness
   objectives.
2. Collect saturation signals for compute, database, queue, cache, network and
   provider quotas where relevant.
3. Preserve correlation across request, job, task and evidence identifiers.
4. Redact secrets and sensitive payloads before broad telemetry exposure.
5. Alert on user-impacting symptoms and error-budget consumption, not only raw CPU.
6. A diagram is not operational evidence; verification requires emitted telemetry.
