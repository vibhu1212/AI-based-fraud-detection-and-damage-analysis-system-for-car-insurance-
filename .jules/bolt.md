## 2024-04-02 - N+1 query performance patterns
**Learning:** When retrieving lists of models in SQLAlchemy, directly accessing un-loaded relationships on the instances causes separate database queries per instance, leading to an N+1 query issue.
**Action:** Explicitly use `joinedload` for many-to-one or one-to-one relationships and `selectinload` for one-to-many relationships when building the initial query. When doing eager-load alongside an explicit `.join()`, remember to use `contains_eager()` instead of `joinedload()`.

## 2024-04-03 - N+1 Memory Bottleneck with In-Memory Sorting
**Learning:** In `backend/app/api/surveyor.py`, paginated API endpoints were fetching the *entire* collection of `Claim` objects into memory (`query.all()`) along with heavily nested relationships (eagerly loaded via `.options()`) solely to perform Python-level sorting. This forces thousands of database rows to be instantiated into SQLAlchemy models in memory for every page request, completely neutralizing the benefits of pagination.
**Action:** Always map complex sorting logic directly into SQL. For enum-based or rule-based sorting (like `RiskLevel`), use SQLAlchemy's `case` statement to generate an ordering weight directly in the `order_by()` clause, followed by `.offset().limit()`. This ensures pagination handles only the required subset of rows, maintaining O(1) memory overhead.
