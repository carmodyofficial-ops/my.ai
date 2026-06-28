# FastAPI + Django Backend Reference

## FastAPI
- Routes: `@app.get("/items/{id}")`, `@app.post(..., status_code=201)`. Return Pydantic models; FastAPI serializes.
- **Async all the way.** `async def` handlers; never call blocking I/O/CPU in them. Wrap sync work: `await run_in_threadpool(fn)` (or `asyncio.to_thread`). One blocking call freezes the whole loop.
- Validation via Pydantic v2: `class ItemIn(BaseModel): name: str; price: float = Field(gt=0)`. v2: `model_dump()`/`model_validate()`, `model_config = ConfigDict(from_attributes=True)` (not v1 `.dict()`/`orm_mode`).
- Separate request vs response models: `@app.post("/i", response_model=ItemOut)` strips internal fields (e.g. password). Never return raw ORM objects.
- Typed params: `id: int` (path), `q: str | None = None` (query) — auto-coerced/validated.
- DI: `def get_db(): db=Session(); try: yield db; finally: db.close()`, then `db: Session = Depends(get_db)`. Same pattern for auth: `user = Depends(get_current_user)`.
- Errors: `raise HTTPException(404, "not found")`. Don't return error dicts.
- `BackgroundTasks` for after-response work: `bg.add_task(send_email, addr)`.
- Docs auto-generated at `/docs` from types — keep annotations accurate.

## Django
- ORM: define `models.Model`; `makemigrations` + `migrate`. **Never edit an applied migration**; create a new one.
- QuerySets are lazy (hit DB on iteration/`list()`). Kill N+1:
  - `select_related("author")` — FK/1:1, SQL JOIN.
  - `prefetch_related("tags")` — M2M/reverse FK, second query.
- Views: CBV (`ListView`, DRF `ModelViewSet`) for CRUD; FBV for one-off logic.
- DRF: `Serializer`/`ModelSerializer` = validation + shaping (Django's Pydantic). Don't expose models raw.
- Forms validate HTML input server-side.
- `admin.site.register(Model)` for free CRUD UI.
- **Secrets via env**: `SECRET_KEY = os.environ["SECRET_KEY"]`; never hardcode in `settings.py`. `DEBUG=False` in prod.

## Gotchas
- Mutable default arg: `def f(x=[])` shares one list — use `x=None; x = x or []`.
- Pydantic v1 vs v2 APIs differ — confirm version before `.dict()` vs `.model_dump()`.
- Forgotten migration = runtime schema drift; run `makemigrations --check` in CI.
