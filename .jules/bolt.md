## 2024-05-24 - Fix N+1 queries in SQLAlchemy
**Learning:** In endpoints that iterate through fetched collections (e.g., looping through `Claim` objects to retrieve `customer.full_name` or `icve_estimates`), SQLAlchemy triggers an N+1 query pattern if relationships are not explicitly eager loaded.
**Action:** Always eagerly load relationships required by the iteration logic using `options(joinedload(...))` for single objects (many-to-one/one-to-one) and `selectinload(...)` for collections (one-to-many) in the initial database query.

## 2024-05-24 - Fix N+1 queries in SQLAlchemy (Revised)
**Learning:** While `joinedload` and `selectinload` are the preferred ways to fix N+1 queries when relationships exist on SQLAlchemy models, blindly adding them without verifying relationship definitions can cause `AttributeError` crashes. Furthermore, using `selectinload` on relationships representing historical tables (e.g., state transitions) fetches the *entire* history into memory, causing a memory/CPU regression if only the latest item is needed.
**Action:** When explicit relationships aren't defined or when fetching history causes memory regressions, use bulk queries with `in_()` on a collected list of IDs. Convert the resulting list into a dictionary mapped by the foreign key to perform O(1) lookups in memory during iteration.
