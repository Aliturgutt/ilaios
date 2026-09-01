# Availability Rules

1. Convert the availability SLO into explicit downtime budgets.
2. Identify critical single points of failure before proposing redundancy.
3. Independent failure domains matter; duplicate instances in one failure domain do
   not prove high availability.
4. Define RTO and RPO independently from availability percentage.
5. Failover capacity must be sized for degraded-mode demand, not just normal demand.
6. Verification requires recovery evidence, not architecture diagrams alone.
