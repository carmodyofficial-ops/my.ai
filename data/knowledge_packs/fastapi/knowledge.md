# FastAPI Reference (dense)

## App & path operations
```python
from fastapi import FastAPI, status
app = FastAPI()

@app.get("/items/{id}")               # path op decorator
async def read(id: int): ...          # id coerced+validated to int

@app.post("/items", status_code=status.HTTP_201_CREATED, response_model=ItemOut)
async def create(item: ItemIn): ...
```
- Methods: `get/post/put/patch/delete/head/options`. Order matters: declare `/users/me` **before** `/users/{id}` (routes match top-down, first match wins).
- Return a dict/Pydantic model/list -> JSON-serialized. Return `Response`/`JSONResponse`/`StreamingResponse` for full control (bypasses `response_model`).

## Params (source inferred by type + declaration)
- **Path**: name in the route + typed arg `id: int` -> required, in URL.
- **Query**: scalar args not in path. `q: str | None = None` (optional); `skip: int = 0`; `list[str]` = repeated `?tag=a&tag=b`.
- **Body**: a Pydantic-model-typed arg. Two models -> keyed JSON `{"item":..,"user":..}`. Single scalar in body: `x: int = Body()`.
- **Validation metadata** via `Query`/`Path`/`Body`/`Field`:
  `q: str = Query(min_length=3, max_length=50, pattern="^a")`, `id: int = Path(ge=1)`, `price: float = Field(gt=0)`. `...` (Ellipsis) or no default = required. In v2 use `pattern=` not `regex=`.
- Headers/cookies: `x: str = Header()`, `s: str = Cookie()`. Forms/files: `File`, `UploadFile`, `Form` (needs `python-multipart`).

## Pydantic (v2) models
```python
from pydantic import BaseModel, Field, ConfigDict, field_validator
class ItemIn(BaseModel):
    name: str
    price: float = Field(gt=0)
    tags: list[str] = Field(default_factory=list)
    @field_validator("name")
    @classmethod
    def strip(cls, v): return v.strip()
class ItemOut(ItemIn):
    model_config = ConfigDict(from_attributes=True)   # read ORM attrs (v1: orm_mode=True)
```
- Body arg -> parsed + validated; malformed -> **422** with a field-level error list.
- `response_model=ItemOut`: validates AND **filters output to the model's fields** — use a separate out-model to hide `password`/internal fields; also `response_model_exclude_unset/none/default=True`.
- v2 API: `model_dump()`/`model_dump_json()` (v1 `.dict()`), `model_validate()` (v1 `parse_obj`), `model_config=ConfigDict(...)` (v1 inner `class Config`).

## Async & the event loop
- `async def` handlers run **on** the event loop. Plain `def` handlers are auto-run in an anyio threadpool (safe for blocking libs).
- **Never block the loop from `async def`**: no `time.sleep`, `requests`, blocking DB drivers, heavy CPU. Offload: `await run_in_threadpool(fn, a)` / `await asyncio.to_thread(fn, a)`, or just make the handler `def`.
- Use async-native drivers under `async def` (`httpx.AsyncClient`, `asyncpg`, SQLAlchemy async engine).

## Dependency injection
```python
from fastapi import Depends
def get_db():
    db = Session()
    try: yield db
    finally: db.close()               # teardown runs after response sent

@app.get("/x")
async def h(db=Depends(get_db), user=Depends(get_current_user)): ...
```
- Nestable, **cached per-request** (same dependency called once/request; opt out `Depends(f, use_cache=False)`). `yield` deps get setup/teardown. Router/app-level deps: `APIRouter(dependencies=[Depends(auth)])`. `Annotated[Session, Depends(get_db)]` is the modern form and reusable.

## Errors & status
```python
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="Not found", headers={"X-E":"1"})

@app.exception_handler(MyErr)
async def h(req, exc): return JSONResponse(status_code=418, content={"m": str(exc)})
```
- 422 = validation (automatic). Return `status_code=` on the decorator for the success code.

## Routers, lifespan, middleware, background
```python
r = APIRouter(prefix="/items", tags=["items"])
@r.get("/")  # -> GET /items/
app.include_router(r)

from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app):
    app.state.pool = await make_pool()   # startup
    yield
    await app.state.pool.close()         # shutdown
app = FastAPI(lifespan=lifespan)         # replaces deprecated on_event

@app.middleware("http")
async def m(req, call_next):
    resp = await call_next(req); resp.headers["X-T"]="1"; return resp

@app.post("/x")
async def h(bg: BackgroundTasks): bg.add_task(write_log, "hi")   # after response
```
- CORS: `app.add_middleware(CORSMiddleware, allow_origins=[...])`. Middleware wraps every request; keep it non-blocking. BackgroundTasks run in the same process **after** the response — not a real job queue (use Celery/ARQ for durability/retries).

## Auth (OAuth2 password + JWT)
```python
oauth2 = OAuth2PasswordBearer(tokenUrl="token")
async def get_current_user(tok: str = Depends(oauth2)):
    try: payload = jwt.decode(tok, SECRET, algorithms=["HS256"])
    except JWTError: raise HTTPException(401, "bad token", headers={"WWW-Authenticate":"Bearer"})
    ...
```
- `Security(dep, scopes=[...])` for scoped/OAuth2 scopes. Hash passwords (`passlib`/bcrypt), never store plaintext.

## Nested models, files, WebSockets, streaming
- Nest models freely; `list[Item]`, `dict[str, Item]`, `Item | None` all validate + document. Use aliases for external field names: `Field(alias="userId")` + `model_config=ConfigDict(populate_by_name=True)`.
- Uploads: `file: UploadFile` (spooled, `await file.read()`), `files: list[UploadFile]`; form fields `Form()`; requires `python-multipart`.
- WebSockets: `@app.websocket("/ws")`, `await ws.accept()`, `await ws.receive_text()/send_text()`; handle `WebSocketDisconnect`. Depends works in ws too.
- Big/streamed responses: return `StreamingResponse(gen())` (SSE/large payloads) to avoid buffering in memory.
- Settings: `pydantic_settings.BaseSettings` reads env/`.env`; inject via `Depends(get_settings)` with `@lru_cache` so it's parsed once.

## Docs / OpenAPI & testing
- Auto OpenAPI: Swagger `/docs`, ReDoc `/redoc`, schema `/openapi.json`. `tags`, `summary`, `description`, docstrings, and `response_model` feed it. Disable in prod: `FastAPI(docs_url=None)`.
```python
from fastapi.testclient import TestClient   # sync, wraps httpx
c = TestClient(app)
assert c.get("/items/1").status_code == 200
# async: httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
# override deps in tests: app.dependency_overrides[get_db] = get_test_db
```

## Gotchas -> Fix
- Blocking call in `async def` (requests/`time.sleep`/sync ORM) freezes **all** concurrent requests -> offload to threadpool or make handler `def`.
- Returning raw ORM objects -> set `response_model` + `ConfigDict(from_attributes=True)` (v1 `orm_mode=True`); otherwise serialization/lazy-load errors.
- `response_model` **filters** output silently -> missing fields usually mean they aren't on the out-model, not a bug.
- Pydantic v1 vs v2 mixed APIs -> confirm version; `regex=`->`pattern=`, `.dict()`->`.model_dump()`, `class Config`->`ConfigDict`.
- Mutable default (`= []`/`= {}`) shared across calls -> use `None` default or `Field(default_factory=list)`.
- Forgetting `await` on an async dep/call -> you get a coroutine object, not data.
- N+1 with an ORM inside a loop -> eager-load (`selectinload`/`joinedload`) or batch; the async runtime won't hide it.
- Route ordering: dynamic `/{id}` above a literal `/me` shadows it -> put literals first.
- Deps run per-request and are cached -> don't rely on a `yield` dep for cross-request singletons; use `lifespan`/`app.state`.
- Big/blocking startup in `@app.on_event` (deprecated) -> use `lifespan`; open pools/clients there, close on shutdown.
- Sending secrets/`docs` in prod -> gate docs, load secrets from env, set `DEBUG`-equivalent behavior off.
