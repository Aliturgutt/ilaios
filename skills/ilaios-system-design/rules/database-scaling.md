# Database Scaling Rules

1. Model read rate, write rate, row/object size, indexes, transaction shape and growth.
2. Optimize queries and indexes before introducing distribution complexity.
3. Use read replicas only when consistency requirements permit replica reads.
4. Partitioning or sharding requires benchmark evidence that simpler strategies are
   insufficient.
5. Define backup, restore, RPO and RTO as part of the data design.
6. Connection limits are a first-class capacity constraint.
7. Tenant isolation must be preserved through every scaling strategy.
