# Caching Rules

1. Introduce a cache only for an identified access pattern or latency/cost constraint.
2. Every cache decision must define keying, TTL/expiry and invalidation semantics.
3. Protect high-demand keys from stampede or thundering-herd behavior.
4. State acceptable staleness and consistency semantics.
5. Treat cache loss as a failure mode and verify origin capacity or graceful shedding.
6. A low cache-hit ratio is a design signal, not a reason to add memory blindly.
