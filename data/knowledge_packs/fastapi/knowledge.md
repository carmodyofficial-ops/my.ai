# FastAPI Reference (dense)

## App & path operations
```python
from fastapi import FastAPI, status
app = FastAPI()

@app.get("/items/{id}")          # path op decorator
async def read(id: int): ...      # id coerced+validated to int

@app.post("/items", status_code=status.HTTP_201_CREATED)
async def create(item: Item): ...
```
Methods: get/post/put/patch/delete. Order matters: declare `/users/me` before `/users/{id}`.

## Params
- **Path**: `id: int` (in route, required).
- **Query**: non-path args. `q: str | None = None` (optional w/ default); `skip: int = 0`. `list[str]` for repeats.
- **Body**: a Pydantic model param. Multiple models or `x: int = Body()` -> keyed JSON.
- **Metadata/validation**: `Query`, `Path`, `Body`:
  `q: str | None = Query(default=None, max_length=50, regex="^a")`, `id: int = Path(ge=1)`. Use `...` (or no default) = required.

## Pydantic models
```python
from pydantic import BaseModel
class Item(BaseModel):
    name: str
    price: float
    tax: float | None = None
```
- Request body: type-hint a param with the model -> parsed+validated, 422 on failure.
- `response_model=ItemOut`: validates AND shapes output, **strips extra fields** (use to hide e.g. passwords). Also `response_model_exclude_unset=True`.

## Async
- `async def` handlers run on the event loop. Plain `def` handlers run in a threadpool automatically.
- **Never block the loop** from `async def`: offload sync/CPU/blocking IO:
  `await run_in_threadpool(fn, a)` or `await asyncio.to_thread(fn, a)`.

## Dependency injection
```python
from fastapi import Depends
def get_db():
    db = Session()
    try: yield db
    finally: db.close()      # teardown after response

@app.get("/x")
async def h(db = Depends(get_db)): ...
```
- Reusable, nestable, cached per-request. Auth: `user = Depends(get_current_user)`.

## Errors
```python
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="Not found")

@app.exception_handler(MyErr)
async def h(req, exc): return JSONResponse(status_code=418, content={...})
```

## APIRouter
```python
r = APIRouter(prefix="/items", tags=["items"])
@r.get("/")...
app.include_router(r)
```

## BackgroundTasks
```python
def write(msg): ...
@app.post("/x")
async def h(bg: BackgroundTasks):
    bg.add_task(write, "hi")   # runs after response
```

## Middleware
```python
@app.middleware("http")
async def m(req, call_next):
    resp = await call_next(req)
    resp.headers["X-T"] = "1"; return resp
```

## Auth (OAuth2 + JWT)
```python
oauth2 = OAuth2PasswordBearer(tokenUrl="token")
async def get_current_user(tok: str = Depends(oauth2)):
    # jwt.decode(tok, SECRET); raise HTTPException(401) on fail
    ...
```
Use `Security(dep, scopes=[...])` for scoped auth.

## Docs
Auto OpenAPI: Swagger `/docs`, ReDoc `/redoc`, schema `/openapi.json`. `tags`, `summary`, docstrings feed it.

## Gotchas -> fix
- Blocking call in `async def` freezes ALL requests -> offload (`to_thread`/`run_in_threadpool`) or use `def`.
- Returning raw ORM objects -> set `response_model` + Pydantic v2 `model_config = ConfigDict(from_attributes=True)` (v1 `orm_mode=True`).
- v2 `model.model_dump()` vs v1 `.dict()`; v2 `model_validate()` vs v1 `parse_obj`.
- Mutable default args (`= []`) -> use `None` default or `Field(default_factory=list)`.
- Forgetting `await` on async deps/calls -> returns a coroutine, not data.
- Skipping Pydantic models -> no validation/docs; always type the body.
- Required vs optional: a default makes it optional; `Query(...)` keeps it required.
