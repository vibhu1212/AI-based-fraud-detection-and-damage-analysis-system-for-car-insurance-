
## 2024-03-05 - Optimizing SQLAlchemy Deletions and Cloud I/O
**Learning:** Bulk-deleting related objects iteratively in SQLAlchemy (e.g. `for item in items: db.query(Model).filter(...).delete()`) causes critical N+1 query patterns. Also, synchronous file deletions (e.g. looping through cloud storage delete commands) heavily block threads on network I/O.
**Action:** Use subqueries and the `.in_()` operator with `synchronize_session=False` to perform bulk deletions in a single query. Wrap synchronous cloud/storage network I/O inside `concurrent.futures.ThreadPoolExecutor` to execute them in parallel.
