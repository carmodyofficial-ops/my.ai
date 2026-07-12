# FastAPI + Django Backend Reference

## Choosing / contrasting
- **Django**: batteries-included (ORM, admin, auth, migrations, forms, templates); sync-first (async views exist but ORM is mostly sync); MVT; best for CRUD-heavy apps, server-rendered pages, teams wanting convention.
- **FastAPI**: async-first API micro-framework; Pydantic validation + auto OpenAPI; bring-your-own ORM/auth/migrations (SQLAlchemy + Alembic); best for high-concurrency JSON/ML APIs.
- DRF ≈ FastAPI+Pydantic layered onto Django's ORM/admin — pick Django+DRF when you also want admin/ORM/migrations for free.

## FastAPI (essentials)
- Routes: `@app.get("/items/{id}")`, `@app.post(..., status_code=201, response_model=ItemOut)`. Return Pydantic models/dicts; FastAPI serializes.
- **Async all the way.** `async def` handlers; never call blocking I/O/CPU in them (one blocking call freezes the whole loop). Wrap sync work: `await run_in_threadpool(fn)` / `asyncio.to_thread`, or make the handler plain `def` (auto threadpool).
- Validation via Pydantic v2: `class ItemIn(BaseModel): name: str; price: float = Field(gt=0)`. v2 uses `model_dump()`/`model_validate()`, `model_config=ConfigDict(from_attributes=True)` (not v1 `.dict()`/`orm_mode`). Bad body -> automatic 422.
- Separate request vs response models: `response_model=ItemOut` strips internal fields (e.g. password). Never return raw ORM objects.
- Typed params: `id: int` (path), `q: str | None = None` (query), `Query/Path(ge=1, max_length=...)` for constraints.
- DI: `def get_db(): db=Session(); try: yield db; finally: db.close()`, then `db=Depends(get_db)`; cached per request; same pattern for `user=Depends(get_current_user)`.
- Errors: `raise HTTPException(404, "not found")` — don't return error dicts. `BackgroundTasks` for after-response work. Docs auto at `/docs`.

## Django ORM
- Define `models.Model`; `python manage.py makemigrations` + `migrate`. **Never edit an applied migration** — create a new one.
- QuerySets are **lazy** (execute on iteration/`list()`/`len()`/slice-materialize/`bool()`) and cached once evaluated.
- Kill N+1:
  - `select_related("author")` — FK/1:1, single SQL JOIN.
  - `prefetch_related("tags")` — M2M/reverse-FK, second query + Python join.
  - `.only(...)`/`.defer(...)` to trim columns; `.values()/.values_list()` for dict/tuple rows (no model instances).
  - `annotate()`/`aggregate()` push counts/sums into SQL instead of Python loops. `F()` for column-relative updates without race; `Q()` for OR/complex filters.
- `bulk_create`/`bulk_update` to avoid per-row round-trips. `.iterator()` for huge result sets (avoids caching all rows).
- Transactions: `with transaction.atomic():` wraps a block; nested = savepoints. `select_for_update()` locks rows (needs atomic). `on_commit(fn)` to fire side-effects only after commit (avoids emitting events for rolled-back data).

## MVT, DRF, admin, forms
- MVT: Model (data) / View (logic; FBV or CBV `ListView`/`DetailView`) / Template (render). URLs route to views.
- DRF: `Serializer`/`ModelSerializer` = validation + shaping (Django's Pydantic). `ModelViewSet` + `router` = full CRUD. `permission_classes`, `authentication_classes`, throttling, pagination built-in. Don't expose models raw.
- Forms (`forms.Form`/`ModelForm`) validate HTML/POST input server-side; `is_valid()` populates `cleaned_data`.
- `admin.site.register(Model)` (or `@admin.register`) = free CRUD UI; customize via `ModelAdmin` (`list_display`, `list_select_related` to fix admin N+1).

## Middleware, signals, settings, caching, async
- Middleware: ordered request/response hooks in `MIDDLEWARE`; order matters (auth before views).
- Signals (`post_save`, `pre_delete`, `m2m_changed`): decouple side-effects — but overuse creates hidden control flow; prefer explicit service functions / model methods for core logic.
- Settings: **secrets via env** — `SECRET_KEY = os.environ["SECRET_KEY"]`; never hardcode. `DEBUG=False` in prod (True leaks tracebacks + settings). Split base/dev/prod settings; keep `ALLOWED_HOSTS` tight.
- Caching: `cache.get/set`, `@cache_page`, per-view/template-fragment; Redis/Memcached backend. Cache expensive querysets, not user-specific secrets.
- Async views (`async def`) supported; ORM calls inside need `sync_to_async()` (ORM is sync). Django is deployed via ASGI (uvicorn/daphne) or WSGI (gunicorn).

## DRF specifics, testing, deploy
- Serializer flow: `s = ItemSerializer(data=request.data); s.is_valid(raise_exception=True); s.save()`. `SerializerMethodField` for computed read fields; nested serializers for related data (mind N+1 — pair with `select_related` in the viewset `queryset`/`get_queryset`).
- ViewSet actions map to HTTP: `list/retrieve/create/update/partial_update/destroy`; add custom with `@action(detail=True)`. Global settings in `REST_FRAMEWORK` (default auth, permissions, pagination, throttle).
- Auth options: session (browser), token, JWT (`djangorestframework-simplejwt`). Permissions: `IsAuthenticated`, `DjangoModelPermissions`, or custom `has_object_permission`.
- Testing: `pytest-django` / `APITestCase`; each test wraps a transaction rolled back after — use `factory_boy` for fixtures. `TestClient`/`APIClient` for endpoint tests.
- Deploy: WSGI (gunicorn) for sync, ASGI (uvicorn/daphne) for async/websockets; `collectstatic` + a CDN/WhiteNoise for static; run `migrate` on deploy; `manage.py check --deploy` for prod hardening.

## Gotchas -> Fix
- **N+1** in templates/serializers (accessing `obj.author` per row) -> `select_related`/`prefetch_related`; check with `django-debug-toolbar` or `connection.queries`.
- Editing an applied migration = schema drift / broken deploys -> new migration; run `makemigrations --check --dry-run` in CI to catch missing ones.
- Migration conflicts (parallel branches) -> `makemigrations --merge`; keep migrations small and reviewed.
- Signal overuse -> hidden side-effects, ordering bugs, hard tests; move core logic to explicit calls, reserve signals for cross-cutting concerns.
- Fat views vs fat models -> business logic belongs in models/services, not sprawling views; keep views thin.
- Settings leakage -> `DEBUG=True` or hardcoded `SECRET_KEY` in prod; env-load and gate.
- Blocking work in a request -> offload to Celery/RQ; Django has no built-in durable queue (FastAPI `BackgroundTasks` isn't durable either).
- Mutable default arg (`def f(x=[])`) shares one list -> `x=None; x = x or []` (applies to both frameworks).
- Pydantic v1 vs v2 API drift -> confirm version before `.dict()` vs `.model_dump()`.
- `QuerySet` re-evaluated in multiple loops -> cache to a list once, or it re-hits the DB.
- Django async view calling sync ORM directly -> `SynchronousOnlyOperation`; wrap in `sync_to_async`.
