# Worked example: Next.js App Router CRUD app (notes, TypeScript, SQLite)

```
notes-app/
├── package.json
├── next.config.ts          # serverExternalPackages for the native sqlite module
├── lib/db.ts               # better-sqlite3 singleton + typed queries
├── components/note-form.tsx  # the ONLY client component (useActionState)
└── app/
    ├── layout.tsx
    ├── page.tsx            # list — server component, direct db call
    ├── loading.tsx
    ├── error.tsx           # must be a client component
    ├── actions.ts          # "use server" create/update/delete + revalidatePath
    └── notes/
        ├── new/page.tsx
        └── [id]/
            ├── page.tsx      # detail + delete form
            └── edit/page.tsx
```

Architecture decisions:
- Server components read the DB **directly** (no API routes, no fetch-to-self). Mutations go through server actions in one `app/actions.ts`; each action calls `revalidatePath` then `redirect`.
- Form actions take `(prevState, formData)` so the client form can use `useActionState` for validation errors + pending state. `id` is bound with `.bind(null, id)` for update/delete.
- `better-sqlite3` is synchronous — fine in server components — and cached on `globalThis` so dev HMR doesn't reopen the file.

`lib/db.ts`:
```ts
import Database from "better-sqlite3";

// Cache on globalThis: Next dev hot-reload re-evaluates modules.
const g = globalThis as unknown as { _db?: Database.Database };

function open(): Database.Database {
  const db = new Database(process.env.DB_PATH ?? "notes.db");
  db.pragma("journal_mode = WAL");
  db.exec(`CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
  )`);
  return db;
}
const db = (g._db ??= open());

export type Note = { id: number; title: string; body: string; updated_at: string };

export function listNotes(): Note[] {
  return db.prepare("SELECT * FROM notes ORDER BY updated_at DESC").all() as Note[];
}
export function getNote(id: number): Note | undefined {
  return db.prepare("SELECT * FROM notes WHERE id = ?").get(id) as Note | undefined;
}
export function insertNote(title: string, body: string): number {
  const info = db.prepare("INSERT INTO notes (title, body) VALUES (?, ?)").run(title, body);
  return Number(info.lastInsertRowid);
}
export function updateNote(id: number, title: string, body: string): void {
  db.prepare("UPDATE notes SET title = ?, body = ?, updated_at = datetime('now') WHERE id = ?")
    .run(title, body, id);
}
export function deleteNote(id: number): void {
  db.prepare("DELETE FROM notes WHERE id = ?").run(id);
}
```

`app/actions.ts`:
```ts
"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { insertNote, updateNote, deleteNote } from "@/lib/db";

export type FormState = { error: string | null };

function parseForm(formData: FormData) {
  return {
    title: String(formData.get("title") ?? "").trim(),
    body: String(formData.get("body") ?? ""),
  };
}

export async function createNoteAction(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const { title, body } = parseForm(formData);
  if (!title) return { error: "Title is required." };
  const id = insertNote(title, body);
  revalidatePath("/");
  redirect(`/notes/${id}`); // redirect() throws, so nothing runs after it
}

// id is pre-bound in the page: updateNoteAction.bind(null, note.id)
export async function updateNoteAction(
  id: number,
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const { title, body } = parseForm(formData);
  if (!title) return { error: "Title is required." };
  updateNote(id, title, body);
  revalidatePath("/");
  revalidatePath(`/notes/${id}`);
  redirect(`/notes/${id}`);
}

export async function deleteNoteAction(id: number): Promise<void> {
  deleteNote(id);
  revalidatePath("/");
  redirect("/");
}
```

## Remaining files

`components/note-form.tsx` — the single client component. It receives the server action as a prop (allowed: server-action references are serializable), so one form serves both create and edit.

```tsx
"use client";

import { useActionState } from "react";
import type { FormState } from "@/app/actions";

type Props = {
  action: (prev: FormState, formData: FormData) => Promise<FormState>;
  defaultValues?: { title: string; body: string };
  submitLabel?: string;
};

export function NoteForm({ action, defaultValues, submitLabel = "Save" }: Props) {
  const [state, formAction, pending] = useActionState(action, { error: null });

  return (
    <form action={formAction} style={{ display: "grid", gap: "0.75rem", maxWidth: 480 }}>
      {state.error && <p role="alert" style={{ color: "crimson" }}>{state.error}</p>}
      <label>
        Title
        <input name="title" defaultValue={defaultValues?.title} required />
      </label>
      <label>
        Body
        <textarea name="body" defaultValue={defaultValues?.body} rows={8} />
      </label>
      <button type="submit" disabled={pending}>
        {pending ? "Saving…" : submitLabel}
      </button>
    </form>
  );
}
```

`app/page.tsx` — list page, server component:

```tsx
import Link from "next/link";
import { listNotes } from "@/lib/db";

// Data lives in SQLite and changes at runtime: never prerender this page statically.
export const dynamic = "force-dynamic";

export default function NotesPage() {
  const notes = listNotes();
  return (
    <main>
      <h1>Notes</h1>
      <p><Link href="/notes/new">+ New note</Link></p>
      {notes.length === 0 ? (
        <p>No notes yet.</p>
      ) : (
        <ul>
          {notes.map((n) => (
            <li key={n.id}>
              <Link href={`/notes/${n.id}`}>{n.title}</Link>{" "}
              <small>{n.updated_at}</small>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
```

`app/notes/[id]/page.tsx` — detail page. In Next 15 `params` is a Promise. Delete is a plain `<form>` posting a pre-bound server action, so it works without any client JS:

```tsx
import Link from "next/link";
import { notFound } from "next/navigation";
import { getNote } from "@/lib/db";
import { deleteNoteAction } from "@/app/actions";

export const dynamic = "force-dynamic";

export default async function NoteDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const note = getNote(Number(id));
  if (!note) notFound();

  return (
    <main>
      <h1>{note.title}</h1>
      <p style={{ whiteSpace: "pre-wrap" }}>{note.body}</p>
      <p>
        <Link href={`/notes/${note.id}/edit`}>Edit</Link> ·{" "}
        <Link href="/">Back to list</Link>
      </p>
      <form action={deleteNoteAction.bind(null, note.id)}>
        <button type="submit">Delete</button>
      </form>
    </main>
  );
}
```

`app/notes/new/page.tsx`:

```tsx
import { createNoteAction } from "@/app/actions";
import { NoteForm } from "@/components/note-form";

export default function NewNotePage() {
  return (
    <main>
      <h1>New note</h1>
      <NoteForm action={createNoteAction} submitLabel="Create" />
    </main>
  );
}
```

`app/notes/[id]/edit/page.tsx`:

```tsx
import { notFound } from "next/navigation";
import { getNote } from "@/lib/db";
import { updateNoteAction } from "@/app/actions";
import { NoteForm } from "@/components/note-form";

export const dynamic = "force-dynamic";

export default async function EditNotePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const note = getNote(Number(id));
  if (!note) notFound();

  return (
    <main>
      <h1>Edit note</h1>
      <NoteForm
        action={updateNoteAction.bind(null, note.id)}
        defaultValues={{ title: note.title, body: note.body }}
      />
    </main>
  );
}
```

`app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = { title: "Notes" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: "2rem auto", maxWidth: 640, padding: "0 1rem" }}>
        {children}
      </body>
    </html>
  );
}
```

`app/loading.tsx`:

```tsx
export default function Loading() {
  return <p>Loading…</p>;
}
```

`app/error.tsx` — error boundaries must be client components:

```tsx
"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main>
      <h1>Something went wrong</h1>
      <p>{error.message}</p>
      <button onClick={reset}>Try again</button>
    </main>
  );
}
```

`next.config.ts` — keep the native module out of the webpack/turbopack bundle:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ["better-sqlite3"],
};

export default nextConfig;
```

`package.json`:

```json
{
  "name": "notes-app",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "better-sqlite3": "^11.10.0",
    "next": "^15.3.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.13",
    "@types/node": "^22.15.0",
    "@types/react": "^19.1.0",
    "@types/react-dom": "^19.1.0",
    "typescript": "^5.8.0"
  }
}
```

`tsconfig.json` needs the `@/*` alias the imports rely on (created by `create-next-app`; the load-bearing part):

```json
{
  "compilerOptions": {
    "paths": { "@/*": ["./*"] },
    "strict": true,
    "jsx": "preserve",
    "module": "esnext",
    "moduleResolution": "bundler",
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"]
}
```

Run: `npm install && npm run dev` — the table is created on first DB access; `notes.db` appears in the project root.

## How a mutation flows through the app

Submitting the edit form runs this sequence: the client form posts its `FormData` to `updateNoteAction` (Next serializes the call over its own POST endpoint — no API route is written by hand). The action validates, writes to SQLite synchronously, calls `revalidatePath("/")` and `revalidatePath("/notes/42")` so both cached RSC payloads are marked stale, then `redirect("/notes/42")` aborts the action by throwing a control-flow exception. The router follows the redirect, re-renders the detail page on the server with fresh data, and streams the result back. While all of that is in flight, `useActionState`'s third return value (`pending`) is `true`, which is what disables the submit button. If validation fails instead, the action returns `{ error }`, `pending` flips back to `false`, and the form re-renders with the message — inputs keep their values because they are uncontrolled (`defaultValue`).

Reads are simpler: list and detail pages are async-free server components that call the query functions in `lib/db.ts` directly during render. `force-dynamic` opts them out of static prerendering, which would otherwise bake build-time database contents into the HTML.

Deployment note: `better-sqlite3` is a native addon, so these routes must run on the Node.js runtime (the default) — do not add `export const runtime = "edge"` anywhere in this app, and the deploy target needs a persistent writable disk for `notes.db` (set `DB_PATH` to an absolute path on the volume).

Common mistakes this example avoids: calling `redirect()` inside a try/catch (it works by throwing); forgetting `revalidatePath` so the list shows stale data after a mutation; marking pages `"use client"` and losing direct DB access; defining server actions inline in client components; using `params.id` without awaiting `params` (Next 15 breaking change).
