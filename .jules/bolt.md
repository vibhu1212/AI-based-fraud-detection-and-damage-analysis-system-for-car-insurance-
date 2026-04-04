## 2024-04-02 - N+1 query performance patterns
**Learning:** When retrieving lists of models in SQLAlchemy, directly accessing un-loaded relationships on the instances causes separate database queries per instance, leading to an N+1 query issue.
**Action:** Explicitly use `joinedload` for many-to-one or one-to-one relationships and `selectinload` for one-to-many relationships when building the initial query. When doing eager-load alongside an explicit `.join()`, remember to use `contains_eager()` instead of `joinedload()`.

## 2025-04-04 - In-memory Pagination and Sorting Bottleneck
**Learning:** Found an N+1 query and memory bottleneck pattern in paginated collections where SQLAlchemy `query.all()` was used to fetch the entire dataset into memory just for Python-level sorting (using `RiskLevel` maps) and slicing (via `itertools.islice`). This leads to severe out-of-memory errors on large datasets.
**Action:** Always map complex or enum-based sorting logic directly into SQL using constructs like `case()` in the `.order_by()` clause, natively followed by `.offset().limit().all()`. Never fetch `query.all()` for Python-level pagination.
