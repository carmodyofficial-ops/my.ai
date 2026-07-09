# Worked Example Dev Stories

Copy-ready templates. Each story below is complete enough to hand to a developer (or agent) and have work start without a follow-up meeting. Steal the skeleton, then imitate the closest worked example.

## Template skeleton (copy this)

```md
# <Type>: <Imperative, specific title>

**Narrative**
As a <role>, I want <capability>, so that <outcome/why>.

**Context**
1–3 sentences: the current behavior, the trigger, the link to code/ticket/incident.

**Scope**
- In: <what this story delivers>
- Out: <explicitly excluded — protects the estimate>

**Acceptance criteria**
- Given <state>, when <action>, then <observable result>.
- Rule: <invariant that must always hold>.

**Technical notes**
- Affected: <files / modules / endpoints>
- Contract/data change: <schema, request/response, migration>
- Approach: <the intended path, not a full design>

**Dependencies**: <stories, services, access, decisions>

**Verification / Done-when**
- [ ] <observable check — command, test, or UI state>

**Estimate**: <points or time> — <one-line basis>
```

Every section earns its place: Narrative gives the *why* (kills gold-plating), Scope-out caps the estimate, AC is the contract, Verification is how anyone confirms done without you.

---

## 1. Bug fix — the best-worked example

```md
# Bug: Login fails silently on Safari (SameSite cookie dropped)

**Narrative**
As a Safari user, I want to stay logged in after submitting the login form,
so that I can use the app instead of bouncing back to the login screen.

**Context**
Since the 4.2 deploy, Safari (macOS + iOS) users report login "does nothing" —
form posts, page reloads to /login. Chrome/Firefox unaffected. Support tickets
#4412, #4419. The session cookie is set with `SameSite=None` but no `Secure`
flag; Safari silently rejects such cookies, so no session is stored.

**Scope**
- In: session cookie attributes so Safari persists the login session.
- Out: password reset, "remember me" duration, CSRF token rotation, other cookies.

**Repro steps**
1. Open Safari 16+ (or iOS Safari). 2. Go to /login. 3. Enter valid creds, submit.
4. Observed: redirected to /login, no session. Expected: land on /dashboard.

**Root-cause hypothesis**
`res.cookie('sid', ..., { sameSite: 'none' })` in `src/auth/session.ts` omits
`secure: true`. Per RFC 6265bis, `SameSite=None` without `Secure` is rejected by
Safari (and increasingly Chrome). Confirm via Safari devtools → Storage → Cookies:
`sid` is absent after POST /login.

**Acceptance criteria**
- Given a valid credential POST on Safari 16+, when the response returns,
  then a `sid` cookie is present with `Secure; HttpOnly; SameSite=None`
  and the next request lands on /dashboard.
- Given the app runs over plain HTTP in local dev, when a cookie is set,
  then `Secure` is omitted (so local login still works).
- Rule: session cookies are never readable by JS (`HttpOnly` always set).

**Technical notes**
- Affected: `src/auth/session.ts` (cookie options), `src/config/env.ts` (isProd flag).
- Approach: set `secure: config.isProduction` alongside `sameSite: 'none'`.
  No API/schema change.

**Dependencies**: none.

**Verification / Done-when**
- [ ] New regression test `session.test.ts`: asserts Set-Cookie header contains
      `Secure` when `NODE_ENV=production`, omits it otherwise. Fails on current main.
- [ ] Manual: log in on real iOS Safari → reach /dashboard, cookie visible in devtools.
- [ ] `npm test` green; no other cookie call sites regress (grep `res.cookie`).

**Estimate**: 2 pts — one-line fix, but cross-browser manual verify + regression test.
```

Why implementable: repro is copy-pasteable, the hypothesis names the exact file/line and a *falsifiable* check, and the AC pins the dev-vs-prod edge case that a naive fix (`secure: true` always) would break.

---

## 2. New API endpoint

```md
# Feature: Add POST /api/notes (create a note)

**Narrative**
As an authenticated user, I want to create a note via the API,
so that the mobile and web clients can persist notes I write.

**Context**
Notes exist read-only (GET /api/notes). Clients currently fake creation client-side.
This adds server-side create with validation and ownership.

**Scope**
- In: POST /api/notes — validate, persist, return the created note.
- Out: update/delete, tags, sharing, attachments, rate limiting.

**API contract**
Request  `POST /api/notes`  (auth: Bearer JWT required)
```json
{ "title": "string (1..120)", "body": "string (0..10000)", "pinned": false }
```
Responses:
- 201 → `{ "id": "uuid", "title", "body", "pinned", "createdAt": "ISO-8601", "ownerId" }`
- 400 → `{ "error": "validation", "fields": { "title": "required" } }`
- 401 → missing/invalid token.

**Validation rules**
- `title`: required, 1–120 chars after trim.
- `body`: optional, ≤10000 chars.
- `pinned`: optional boolean, default false.
- Unknown fields rejected (400), not silently dropped.

**Acceptance criteria**
- Given a valid token + body, when POST /api/notes, then 201 with the persisted
  note and `ownerId` = the token's user (never client-supplied).
- Given `title` empty/missing, when POST, then 400 with `fields.title`.
- Given no/invalid token, when POST, then 401 and nothing is written.
- Rule: `ownerId` is derived from the auth context, never the request body.

**Technical notes**
- Affected: `routes/notes.ts` (add handler), `schemas/note.ts` (zod schema),
  `db/notes.repo.ts` (insert), `openapi.yaml` (document).
- Data: reuse `notes` table; `owner_id` FK → users.id.
- Approach: validate with zod → repo.insert → 201. Reuse existing auth middleware.

**Dependencies**: auth middleware (exists); DB migration for `notes` (already shipped).

**Verification / Done-when**
- [ ] Integration tests: 201 happy path, 400 (empty title), 400 (unknown field),
      401 (no token), ownerId-from-token (ignores body-supplied ownerId).
- [ ] `curl -X POST .../api/notes -H "Authorization: Bearer $T" -d '{"title":"hi"}'` → 201.
- [ ] openapi.yaml updated; `npm run lint:openapi` passes.

**Estimate**: 3 pts — new route, schema, 5 tests, doc.
```

Why implementable: the contract is a spec, not a wish — every status code has a shaped body, and the "ownerId from token" rule closes the classic mass-assignment hole. Tests map 1:1 to the AC.

---

## 3. UI component

```md
# Feature: Notes list component with empty / loading / error states

**Narrative**
As a user, I want the notes screen to clearly show loading, empty, and error
conditions, so that I'm never staring at a blank page wondering if it broke.

**Context**
Current `<NotesList>` renders `notes.map(...)` and shows nothing while fetching
or on failure — indistinguishable from "you have no notes."

**Scope**
- In: four render states (loading, error+retry, empty, populated); a11y; responsive.
- Out: pagination, search/filter, create/edit UI, optimistic updates.

**States**
- Loading: 3 skeleton rows (not a spinner-only), `aria-busy="true"`.
- Error: message + "Retry" button that re-invokes the fetch.
- Empty: illustration + "No notes yet" + "Create your first note" CTA.
- Populated: list of note cards (title, snippet, timestamp).

**Acceptance criteria**
- Given the fetch is in flight, when rendered, then skeletons show and no
  "empty" copy appears.
- Given the fetch rejects, when rendered, then an error message + working Retry
  button show; clicking Retry refetches.
- Given the fetch resolves to `[]`, when rendered, then the empty state + CTA show.
- Given results, when rendered, then each note is a card; list is keyboard-navigable.
- Rule: exactly one state renders at a time (no skeleton + data overlap).

**Technical notes**
- Affected: `components/NotesList.tsx`, `components/NotesList.test.tsx`,
  `components/ui/Skeleton.tsx` (reuse).
- Approach: derive state from the query hook (`isLoading|isError|data`); early-return
  per state. a11y: list uses `<ul role="list">`, error uses `role="alert"`.
- Responsive: 1 col < 640px, 2 cols ≥ 640px (existing grid utility).

**Dependencies**: notes query hook (exists); design tokens for skeleton/illustration.

**Verification / Done-when**
- [ ] RTL tests for all four states + Retry click → refetch called.
- [ ] `axe` check: 0 violations in each state.
- [ ] Manual: keyboard tab through list; throttle network to see loading;
      offline to see error.

**Estimate**: 3 pts — 4 states, a11y, tests.
```

Why implementable: states are enumerated with concrete visuals (skeletons, not "a loader"), the "exactly one state" rule prevents the flicker bug, and a11y is an AC, not an afterthought.

---

## 4. Refactor (no behavior change)

```md
# Refactor: Extract email sending into an EmailService (no behavior change)

**Narrative**
As a developer, I want email sending behind one EmailService,
so that I can swap providers and test call sites without duplicated SMTP code.

**Context**
`nodemailer` is called inline in 4 places (signup, reset, invite, receipt), each
re-building transport + templates. Duplication makes provider swap and testing hard.

**Scope**
- In: introduce `src/services/EmailService.ts`; route all 4 call sites through it.
- Out: changing providers, template copy, adding retries/queueing, new emails.

**Acceptance criteria (no-behavior-change)**
- Given each existing flow (signup/reset/invite/receipt), when triggered, then the
  same recipient, subject, and body are sent as before the refactor.
- Given the test suite, when run before and after, then the same tests pass with no
  assertion changes to observable behavior.
- Rule: no new outbound email, no changed timing, no changed error propagation.

**Technical notes**
- Affected: `services/EmailService.ts` (new), `auth/signup.ts`, `auth/reset.ts`,
  `team/invite.ts`, `billing/receipt.ts` (call sites), delete inline transport.
- Approach: EmailService exposes `send(to, template, data)`; move transport +
  template lookup inside. Pure move — same inputs, same outputs.

**Dependencies**: none — internal move.

**Verification / Done-when**
- [ ] Characterization tests written FIRST against current behavior (capture the
      exact sent payloads with a mock transport) — must pass on main before refactor.
- [ ] Same characterization tests pass unchanged after refactor.
- [ ] `git grep nodemailer` returns only `EmailService.ts`.
- [ ] Diff review: no `.subject`/`.html` string changed.

**Estimate**: 3 pts — mechanical, but characterization tests gate correctness.
```

Why implementable: "no behavior change" is made testable by writing characterization tests *first* against the old code, and the grep gives a binary done-check that the duplication is actually gone.

---

## 5. Data migration (expand / contract)

```md
# Migration: Add nullable `notes.archived_at`, backfill, expand→contract

**Narrative**
As a user, I want to archive notes instead of deleting them,
so that I can hide clutter without losing content.

**Context**
Notes are hard-deleted. Product wants archive (reversible). Needs a new column,
safe rollout with zero downtime, and no break to the running old code.

**Scope**
- In: migration adding `archived_at timestamptz null`; backfill NULL; app reads/writes it.
- Out: the archive UI, list-filtering by archive, purge job, delete removal.

**Migration steps (expand/contract)**
1. Expand: `ALTER TABLE notes ADD COLUMN archived_at timestamptz NULL;`
   (nullable → old code ignores it, keeps working — backward compatible.)
2. Backfill: none needed (NULL = "not archived" is the correct default).
3. Deploy app that writes/reads `archived_at`.
4. Contract (later story): add partial index / drop legacy delete path — NOT here.

**Acceptance criteria**
- Given the migration runs on a populated DB, when complete, then every existing
  row has `archived_at IS NULL` and no row is locked >1s.
- Given old app code (pre-deploy), when it reads/writes notes, then it works
  unchanged (column is nullable, not in its INSERT column list).
- Rule: migration is reversible — a down migration drops the column cleanly.

**Technical notes**
- Affected: `migrations/2026__add_archived_at.sql` (up+down),
  `db/notes.repo.ts` (select/insert include archived_at), `types/Note.ts`.
- Rollback: `ALTER TABLE notes DROP COLUMN archived_at;` (safe — no other refs yet).
- Approach: additive nullable column = no table rewrite in Postgres; instant.

**Dependencies**: run in a maintenance-safe window? No — additive+nullable is online-safe.

**Verification / Done-when**
- [ ] `migrate up` then `migrate down` both succeed on a copy of prod-shaped data.
- [ ] Post-up: `SELECT count(*) FROM notes WHERE archived_at IS NOT NULL;` → 0.
- [ ] Old-image smoke test still passes against migrated DB (backward compat).
- [ ] `EXPLAIN ANALYZE` shows the ALTER did not rewrite the table.

**Estimate**: 2 pts — additive migration; care is in reversibility + compat proof.
```

Why implementable: it names the expand/contract sequence explicitly, proves backward-compat (old code against new schema), and the down migration + no-rewrite check make rollback and safety observable, not assumed.

---

## 6. Agent-ready task (same work, autonomous-coding-agent form)

Same fix as #1, rewritten so an autonomous agent can execute with no human in the loop. Note the deltas: absolute paths, a *provided failing test*, exact commands, expected output, and guardrails.

```md
# Agent task: Make session cookies Safari-compatible (Secure flag)

**Goal**: The session cookie must carry `Secure` in production so Safari persists it.

**Start state**: On `main`, `src/auth/session.ts` sets the `sid` cookie with
`sameSite: 'none'` and no `secure` flag.

**Failing test to make pass** (already added at
`test/auth/session.secure.test.ts` — do NOT edit it):
```ts
it('sets Secure in production, omits it in dev', () => {
  process.env.NODE_ENV = 'production';
  expect(buildCookieOptions().secure).toBe(true);
  process.env.NODE_ENV = 'development';
  expect(buildCookieOptions().secure).toBe(false);
});
```

**Files you MAY change**: `src/auth/session.ts`, `src/config/env.ts`.
**Files you must NOT change**: anything under `test/`, `src/billing/`, `openapi.yaml`.

**Steps**
1. Run `npm test -- session.secure` → confirm it FAILS (red baseline).
2. In `src/auth/session.ts`, export `buildCookieOptions()` returning cookie opts
   with `secure: isProduction()`, `httpOnly: true`, `sameSite: 'none'`.
3. Use `isProduction()` from `src/config/env.ts` (add it if absent: `NODE_ENV==='production'`).

**Guardrails**
- Do not remove `httpOnly` or `sameSite`. Do not touch other `res.cookie` calls.
- No new dependencies. Keep the diff under ~20 lines.
- If the fix would require editing a test, STOP and report — the test is the spec.

**Verification (run exactly this)**
- `npm test -- session.secure` → expect: `Tests: 2 passed`.
- `npm run typecheck` → expect: exit 0.
- `git grep -n "res.cookie" src/` → expect: only `src/auth/session.ts` matches.

**Done-when**: both commands above pass and the diff touches only the two allowed files.
```

Why implementable by an agent: the spec is a failing test (unambiguous target), every verification has a literal expected output, and guardrails bound the blast radius (allowed/forbidden files, diff size, "stop if you'd edit a test").

---

## Pitfalls → Fix

- **Cargo-culting the template** (copying section headers, filling them with air) → Fill each section with a *specific, checkable* line or delete the section. A Scope-out of "N/A" means you haven't thought about scope.
- **Dropping Scope-out** → Estimates balloon and reviewers argue over what's "in." Always list at least 2 exclusions; they are the cheapest scope control you have.
- **Untestable AC** ("works well", "is fast", "handles errors") → Rewrite as Given/When/Then with an observable result, or as a rule with a value/threshold. If you can't write the test, the AC isn't done.
- **Narrative as decoration** → If "so that" is missing or generic ("so that it works"), you can't tell gold-plating from requirement. Make the *why* real.
- **Verification that only says "tests pass"** → Name *which* tests/commands and their expected output; for agent tasks, provide the failing test up front so "done" is binary.
- **Contract by example only** → One sample request isn't a spec. Enumerate status codes, validation rules, and the auth/ownership invariants (mass-assignment is where examples silently pass but security fails).
