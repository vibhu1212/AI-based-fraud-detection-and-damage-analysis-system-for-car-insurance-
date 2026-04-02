## 2024-03-24 - Eager Loading Relationships in SQLAlchemy

**Learning:** When retrieving collections in SQLAlchemy, querying related objects (like a user's `Claim` entities, along with the `User` and `ICVEEstimate` relationships) inside a loop causes a severe N+1 query problem that drastically affects backend performance.

**Action:** Always proactively review loops iterating over SQLAlchemy models for related object accesses. Replace lazy-loading approaches inside loops by modifying the initial query to use eager loading: `joinedload` for many-to-one/one-to-one relationships to prevent Cartesian products, and `selectinload` for one-to-many collection relationships.
