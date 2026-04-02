## 2024-05-18 - N+1 Query on ICVE Estimates
**Learning:** `Claim.icve_estimates` relationship is frequently accessed when iterating over collections of claims (e.g. `get_customer_dashboard`), causing an N+1 query problem. This can be resolved with eager loading.
**Action:** Use `selectinload` for `icve_estimates` when querying collections of `Claim` objects.
