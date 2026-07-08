# Web Testing (Playwright, Vitest, Testing Library)

## Playwright locators — role-first
- Priority: `getByRole('button', { name: 'Save' })` > `getByLabel('Email')` > `getByPlaceholder` > `getByText` > `getByTestId('checkout')` > CSS/XPath (last resort — brittle, tests implementation).
- `name` matches the accessible name (visible text, aria-label, alt); use `{ name: /save/i }` regex for case-insensitive, `{ exact: true }` on getByText to stop substring matches.
- Chain/filter: `page.getByRole('listitem').filter({ hasText: 'Milk' }).getByRole('button', { name: 'Remove' })`.
- Strict mode: a locator resolving to 2+ elements throws on action — disambiguate with `.first()` (smell), `filter`, or `nth()`; better: tighten the query.
- Locators are lazy — re-evaluated at action time; safe to define before the element exists.

## Auto-waiting & assertions
- Actions (`click`, `fill`) auto-wait for visible/stable/enabled/attached — never add `waitForTimeout` for element readiness.
- Web-first assertions retry until timeout: `await expect(locator).toBeVisible() / toHaveText() / toHaveCount(3) / toHaveURL(/dashboard/)`. Plain `expect(await locator.textContent())` does NOT retry — top flake source.
- `await expect(locator).not.toBeVisible()` also retries — correct way to await disappearance (spinners).
- Timeouts: action 30s default (config `timeout`), `expect` 5s (`expect: { timeout }`); override per-call `toBeVisible({ timeout: 10_000 })`.

## Fixtures & structure
- Custom fixtures beat beforeEach for shared setup:
```ts
export const test = base.extend<{ todoPage: TodoPage }>({
  todoPage: async ({ page }, use) => { const t = new TodoPage(page); await t.goto(); await use(t); },
});
```
- Auth once per run: a `setup` project writes `storageState` to disk (`page.context().storageState({ path })`); other projects set `storageState` in `use` and depend on it via `dependencies: ['setup']`.
- Tests run in parallel across worker processes by default; each test gets a fresh browser context (cookies/storage isolated). `test.describe.configure({ mode: 'serial' })` only for genuinely ordered flows.
- `worker`-scoped fixtures for expensive per-process resources (DB seed, server).

## Network mocking
- `await page.route('**/api/todos', route => route.fulfill({ json: [{ id: 1, title: 'x' }] }))` — must be set BEFORE the navigation/action that triggers the request.
- Modify real responses: `const res = await route.fetch(); await route.fulfill({ response: res, json: patch(await res.json()) })`.
- Fail/delay: `route.abort()`, or `setTimeout` before fulfill for slow-network tests.
- Wait for a request: `const resPromise = page.waitForResponse('**/api/save'); await button.click(); const res = await resPromise` — create the promise before the action.
- HAR replay: `page.routeFromHAR('fixtures/api.har', { update: false })` for full offline runs.

## Trace, debug, CI
- `trace: 'on-first-retry'` in config; view with `npx playwright show-trace trace.zip` — DOM snapshots, network, console per action. The single best flake-debugging tool.
- `npx playwright test --ui` (watch mode + time-travel), `--debug` (Inspector, step through), `page.pause()` mid-test.
- `npx playwright codegen URL` records actions into role-based locators — good starting point, then refactor.
- CI: `retries: 2`, `workers: 1` only if tests share state (fix that instead), upload `playwright-report/` + traces as artifacts; run against a production build, not dev server with HMR.

## Vitest / Jest unit patterns
- Vitest: Jest-compatible API, native ESM/TS, `vi.fn()` / `vi.mock('./module')` (hoisted — use `vi.hoisted` for referenced vars), `vi.useFakeTimers()` + `await vi.advanceTimersByTimeAsync(1000)` for async timer code.
- `vi.mock` with a factory replaces the whole module; `vi.spyOn(obj, 'method')` for partial + restore (`vi.restoreAllMocks` in afterEach or config `restoreMocks: true`).
- Mock fetch at the network edge with MSW (`setupServer(http.get('/api/user', () => HttpResponse.json({...})))`) — survives refactors from fetch to axios; reset handlers between tests.
- Test behavior, not implementation: assert on rendered output/returned values, not "function X was called with Y" unless the call IS the contract.

## Testing Library queries
- Same priority as Playwright: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`.
- `getBy*` throws if missing (use for "exists now"); `queryBy*` returns null (use for asserting absence); `findBy*` returns a promise that retries (use after async updates — `await screen.findByText('Saved')`).
- Interactions: `userEvent.setup()` then `await user.click(...)` — fires full event sequences (pointer, focus, keyboard) unlike bare `fireEvent`.
- "not wrapped in act(...)" warning = an un-awaited state update; await the `findBy*`/userEvent promise instead of sprinkling `act()`.

## Config essentials & extras
- `playwright.config.ts` core: `projects` per browser (`chromium`/`firefox`/`webkit` via `devices['Desktop Chrome']`), `use: { baseURL, trace, screenshot: 'only-on-failure' }`, `fullyParallel: true`, `forbidOnly: !!process.env.CI`.
- Visual regression: `await expect(page).toHaveScreenshot('home.png', { maxDiffPixelRatio: 0.01 })` — snapshots are per-OS/browser; generate baselines in CI's environment (or a docker image), not your laptop.
- Accessibility gate: `@axe-core/playwright` — `expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])`.
- Component testing exists (`@playwright/experimental-ct-react`) but most teams get better ROI from Vitest + Testing Library for components and Playwright for flows.
- Tagging: `test('checkout @smoke', ...)` + `--grep @smoke` for fast PR suites vs full nightly runs.

## Flaky tests: causes -> fixes
- **Manual sleeps (`waitForTimeout`)**: replace with web-first assertions or `waitForResponse`.
- **Non-retrying assertion on async UI**: `expect(await el.textContent())` → `await expect(el).toHaveText(...)`.
- **Shared state across parallel tests** (same user account, same DB row): unique per-test data (faker + worker index) or serial-ize the true dependencies.
- **Race: assert before request lands**: set up `waitForResponse`/`page.route` before the triggering click.
- **Animations mid-click**: Playwright waits for stability, but CSS transition end-states can still race — disable animations in test env (`reducedMotion: 'reduce'` in `use`, or a test-only stylesheet).
- **Date/time-dependent logic**: fake the clock (`page.clock.setFixedTime(...)` in Playwright ≥1.45; `vi.setSystemTime` in Vitest).
- **First-load flake on cold dev server**: test against built output; `webServer: { command: 'npm run preview', reuseExistingServer: !process.env.CI }`.
- **Test passes alone, fails in suite**: leaked module state or unreset mocks — `restoreMocks`/`clearMocks: true`, MSW `server.resetHandlers()` in afterEach.
- **Dialog/confirm silently auto-dismissed**: Playwright dismisses native dialogs by default — register `page.on('dialog', d => d.accept())` before triggering.
- **New-tab flows lose the page**: `const [popup] = await Promise.all([page.waitForEvent('popup'), link.click()])` — grab the popup from the event, then assert on it.
- **File download assertions hang**: use `page.waitForEvent('download')` around the click and `download.path()`/`suggestedFilename()`; downloads need `acceptDownloads` (default on).
- **Hover-dependent menu never opens in CI**: no real pointer — use `locator.hover()` explicitly; headless has no incidental mouse position.
