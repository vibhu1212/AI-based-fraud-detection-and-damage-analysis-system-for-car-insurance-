## 2024-04-02 - N+1 query performance patterns
**Learning:** When retrieving lists of models in SQLAlchemy, directly accessing un-loaded relationships on the instances causes separate database queries per instance, leading to an N+1 query issue.
**Action:** Explicitly use `joinedload` for many-to-one or one-to-one relationships and `selectinload` for one-to-many relationships when building the initial query. When doing eager-load alongside an explicit `.join()`, remember to use `contains_eager()` instead of `joinedload()`.
