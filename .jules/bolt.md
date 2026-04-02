## 2024-05-24 - [SQLAlchemy N+1 Query on Collection Relationships]
**Learning:** In SQLAlchemy, when fetching collection relationships (like `Claim.icve_estimates`) for a list of objects and then iterating over them, it causes severe N+1 query problems.
**Action:** Always use `selectinload` (instead of `joinedload`) to eager load collection relationships in list queries to prevent the N+1 queries without causing Cartesian product regressions.
