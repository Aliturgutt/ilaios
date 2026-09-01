# Load Balancing and Overload Rules

1. Load balancing distributes admitted traffic; it does not replace admission control.
2. Define health signals that remove unhealthy capacity without causing failover loops.
3. Keep enough healthy headroom to survive expected node/failure-domain loss.
4. Pair internet-facing services with rate limiting and overload shedding.
5. Avoid session affinity unless state or protocol requirements justify it.
6. Validate balancing behavior under uneven latency and partial failure.
