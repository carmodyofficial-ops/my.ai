# Worked example: full-stack FastAPI + React (Vite, TypeScript, TanStack Query, SQLite)

```
notes/
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py         # FastAPI app, lifespan creates tables, CORS
│       ├── db.py           # sqlmodel engine + session dependency
│       ├── models.py       # one SQLModel table + create/update schemas
│       └── routes.py       # CRUD router under /api/notes
└── frontend/
    ├── package.json
    ├── vite.config.ts      # dev proxy: /api → http://localhost:8000
    ├── index.html
    └── src/
        ├── main.tsx        # QueryClientProvider
        ├── App.tsx
        ├── api.ts          # typed fetch wrapper — the single HTTP boundary
        ├── hooks.ts        # TanStack Query: useNotes/useCreateNote/useDeleteNote
        └── components/{NoteForm.tsx, NoteList.tsx}
```

Architecture decisions:
- Backend owns all routes under `/api/*`. In dev the Vite proxy forwards `/api` to uvicorn, so the browser sees one origin and `fetch("/api/notes")` needs no absolute URL. CORS middleware is still configured for the no-proxy case (frontend on :5173 hitting :8000 directly).
- One `sqlmodel` class is both the SQLAlchemy table and the pydantic response model; separate `NoteCreate`/`NoteUpdate` schemas keep `id` out of request bodies.
- Frontend components never call `fetch`; they use hooks, hooks use the typed client in `api.ts`. Mutations invalidate the `["notes"]` query key instead of hand-patching caches.

`backend/app/models.py`:
```python
from sqlmodel import Field, SQLModel


class NoteBase(SQLModel):
    title: str
    body: str = ""


class Note(NoteBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class NoteCreate(NoteBase):
    pass


class NoteUpdate(SQLModel):  # all optional: PATCH semantics
    title: str | None = None
    body: str | None = None
```

`frontend/src/api.ts`:
```ts
export type Note = { id: number; title: string; body: string };
export type NoteCreate = { title: string; body?: string };

const BASE = "/api"; // Vite proxies this to the backend in dev

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  listNotes: () => request<Note[]>("/notes"),
  createNote: (data: NoteCreate) =>
    request<Note>("/notes", { method: "POST", body: JSON.stringify(data) }),
  deleteNote: (id: number) =>
    request<void>(`/notes/${id}`, { method: "DELETE" }),
};
```

## Backend — remaining files

`backend/app/db.py`:

```python
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

# check_same_thread=False: FastAPI may hit SQLite from different threads.
engine = create_engine(
    "sqlite:///notes.db", connect_args={"check_same_thread": False}
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
```

`backend/app/routes.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .db import get_session
from .models import Note, NoteCreate, NoteUpdate

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("", response_model=list[Note])
def list_notes(session: Session = Depends(get_session)) -> list[Note]:
    return list(session.exec(select(Note).order_by(Note.id.desc())).all())


@router.post("", response_model=Note, status_code=201)
def create_note(
    payload: NoteCreate, session: Session = Depends(get_session)
) -> Note:
    note = Note.model_validate(payload)
    session.add(note)
    session.commit()
    session.refresh(note)  # populate the generated id before returning
    return note


@router.get("/{note_id}", response_model=Note)
def get_note(note_id: int, session: Session = Depends(get_session)) -> Note:
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=Note)
def update_note(
    note_id: int, payload: NoteUpdate, session: Session = Depends(get_session)
) -> Note:
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, key, value)
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: int, session: Session = Depends(get_session)) -> None:
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    session.delete(note)
    session.commit()
```

`backend/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables on startup (use Alembic once schemas evolve)
    yield


app = FastAPI(title="Notes API", lifespan=lifespan)

# Only needed if the browser talks to :8000 directly (no Vite proxy).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
```

`backend/app/__init__.py` is empty. `backend/requirements.txt`:

```
fastapi>=0.115
sqlmodel>=0.0.24
uvicorn[standard]>=0.34
```

## Frontend — remaining files

`frontend/src/hooks.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type NoteCreate } from "./api";

const notesKey = ["notes"] as const;

export function useNotes() {
  return useQuery({ queryKey: notesKey, queryFn: api.listNotes });
}

export function useCreateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: NoteCreate) => api.createNote(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: notesKey }),
  });
}

export function useDeleteNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteNote(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: notesKey }),
  });
}
```

`frontend/src/components/NoteForm.tsx`:

```tsx
import { useState, type FormEvent } from "react";
import { useCreateNote } from "../hooks";

export function NoteForm() {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const createNote = useCreateNote();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    createNote.mutate(
      { title: title.trim(), body },
      {
        onSuccess: () => {
          setTitle("");
          setBody("");
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.5rem" }}>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Title"
        required
      />
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Body"
        rows={4}
      />
      <button type="submit" disabled={createNote.isPending}>
        {createNote.isPending ? "Adding…" : "Add note"}
      </button>
      {createNote.isError && (
        <p role="alert" style={{ color: "crimson" }}>{createNote.error.message}</p>
      )}
    </form>
  );
}
```

`frontend/src/components/NoteList.tsx`:

```tsx
import { useDeleteNote, useNotes } from "../hooks";

export function NoteList() {
  const { data: notes, isPending, isError, error } = useNotes();
  const deleteNote = useDeleteNote();

  if (isPending) return <p>Loading…</p>;
  if (isError) return <p role="alert">Failed to load notes: {error.message}</p>;
  if (notes.length === 0) return <p>No notes yet.</p>;

  return (
    <ul>
      {notes.map((note) => (
        <li key={note.id}>
          <strong>{note.title}</strong>
          {note.body && <p>{note.body}</p>}
          <button
            onClick={() => deleteNote.mutate(note.id)}
            disabled={deleteNote.isPending}
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  );
}
```

`frontend/src/App.tsx`:

```tsx
import { NoteForm } from "./components/NoteForm";
import { NoteList } from "./components/NoteList";

export default function App() {
  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h1>Notes</h1>
      <NoteForm />
      <NoteList />
    </main>
  );
}
```

`frontend/src/main.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
```

`frontend/index.html`:

```html
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
```

`frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
});
```

`frontend/package.json`:

```json
{
  "name": "notes-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.66.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@types/react": "^19.1.0",
    "@types/react-dom": "^19.1.0",
    "@vitejs/plugin-react": "^4.4.0",
    "typescript": "^5.8.0",
    "vite": "^6.3.0"
  }
}
```

## Running both in dev

Two terminals:

```bash
# terminal 1 — backend on :8000 (creates notes.db on startup)
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend on :5173
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Requests to `/api/*` are proxied by Vite to uvicorn, so no CORS preflight occurs in normal dev. Interactive API docs live at http://localhost:8000/docs.

## How a request flows through the stack

Creating a note: `NoteForm` calls `createNote.mutate({title, body})` → the mutation's `mutationFn` calls `api.createNote`, which sends `POST /api/notes` with a JSON body → Vite's dev server sees the `/api` prefix and forwards the request to `http://localhost:8000` → FastAPI validates the body against `NoteCreate` (a 422 with field-level errors comes back automatically if it fails), `create_note` inserts the row and returns the `Note` with its generated `id` → on the 201 response, the mutation's `onSuccess` invalidates `["notes"]`, TanStack Query refetches `GET /api/notes`, and every component using `useNotes` re-renders with the new list. Deletes follow the same shape; the 204 branch in `request()` is why `deleteNote` resolves to `undefined` instead of choking on an empty body.

The layering rule that keeps this maintainable: `api.ts` is the only file that knows about HTTP and response shapes, `hooks.ts` is the only file that knows about cache keys and invalidation, and components only know hooks. Adding an "update note" feature touches exactly three places — a `NoteUpdate` type plus `api.updateNote`, a `useUpdateNote` hook, and whichever component needs it — with no changes to existing code paths.

For production, run `npm run build` and serve `frontend/dist` from any static host (or mount it in FastAPI with `app.mount("/", StaticFiles(directory="dist", html=True))` after the API router); once frontend and API share an origin, the CORS middleware can be dropped entirely.

Common mistakes this example avoids: components calling `fetch` directly instead of going through hooks + the typed client; forgetting `invalidateQueries` after a mutation so the list goes stale; returning the created row without `session.refresh` (id would be `None`); accepting `id` in POST bodies by reusing the table model as the request schema; hardcoding `http://localhost:8000` in the frontend so the proxy and production deploys both break.
