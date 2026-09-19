# Queue Rules

1. Use queues to decouple work only when asynchronous semantics are acceptable.
2. Every queued side effect requires an idempotency contract.
3. Retries must be bounded and use backoff; retry amplification is a failure mode.
4. Poison messages require dead-letter or equivalent bounded handling.
5. Observe oldest-message age, backlog growth and consumer throughput.
6. Scale consumers only after verifying downstream capacity.
7. Delivery semantics must be explicit; do not infer exactly-once behavior from a
   queue product name.
