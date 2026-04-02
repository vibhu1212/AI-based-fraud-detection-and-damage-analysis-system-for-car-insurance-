## 2024-05-20 - N+1 Queries in Loops
**Learning:** Explicit loop queries (e.g., `db.query(User).filter(User.id == claim.customer_id).first()`) introduced massive N+1 bottlenecks.
**Action:** Preload necessary relations upfront using SQLAlchemy eager loading (`joinedload` for many-to-one, `selectinload` for one-to-many) to condense database round trips into fewer constant queries.
