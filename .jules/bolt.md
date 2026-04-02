## 2026-03-20 - [N+1 query issue avoided by not missing memory context]

## 2024-05-24 - N+1 query vulnerability due to lazy loaded relationships
**Learning:** Found N+1 query bottleneck across surveyor endpoints: `get_surveyor_inbox`, `get_surveyor_overview`, and `get_surveyor_reports` iterating over queries fetching User relationships and `claim.icve_estimates` relationships per row causing major performance bottlenecks when working with a list of claims.
**Action:** Used SQLAlchemy`s `joinedload` and `selectinload` to eager load the `customer` and `icve_estimates` on the claims list queries instead of performing queries in the loop.
