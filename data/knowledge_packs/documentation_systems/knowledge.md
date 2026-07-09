# Documentation Systems

## Diataxis framework (organize docs by user need)
- Four distinct modes, each with a different reader intent — never blend them in one page:
  - **Tutorial** (learning): guided, guaranteed-success lesson for a beginner; you drive, no choices, no theory.
  - **How-to guide** (a task): steps to solve one real-world goal; assumes competence; offers a recipe.
  - **Reference** (information): austere, complete, consistent lookup material (API, CLI flags, config keys); structured by the product, not the reader's journey.
  - **Explanation** (understanding): the why — background, context, trade-offs, design decisions; read away from the machine.
- Axes: tutorial/how-to are *action*; reference/explanation are *cognition*. Tutorial/explanation serve *study*; how-to/reference serve *work*.
- Litmus test: if a page teaches AND lists API params AND argues design, split it into three linked pages.

## Docs-as-code (treat docs like software)
- Store docs in version control (Git) alongside or near the code they describe.
- Author in plain-text markup: Markdown, MDX, reStructuredText, AsciiDoc.
- Review docs via pull requests; docs changes get the same review rigor as code.
- CI on docs: build the site, run link checkers, spell/style linters (Vale), test code snippets.
- Benefits: diff-able history, branchable, review workflow, doc changes ship with the code change in the same PR.
- "Definition of done" for a feature includes updated docs.

## API documentation
- Spec-first: describe REST APIs in OpenAPI (Swagger); GraphQL is self-describing via schema/introspection; gRPC via `.proto`.
- Auto-generate reference from the spec (Swagger UI, Redoc, Stoplight) so it can't drift from the contract.
- Per endpoint document: method + path, auth, params (type/required/default), request body, every response code, error shapes, and a runnable example (curl + one real language).
- Show real request/response payloads, not just schemas.
- Reference (generated) is necessary but not sufficient — pair with hand-written how-to guides ("authenticate", "paginate", "handle rate limits") and a quickstart.

## README essentials (the front door)
- What it is (one line) + why it exists.
- Quickstart: install + minimal working example that runs in under 5 minutes.
- Prerequisites, install/setup, basic usage with copy-paste commands.
- Links to fuller docs, contributing guide, license, support/issues.
- Badges (build, version) for at-a-glance status; keep the top scannable.

## Information architecture + navigation
- Structure by user task/journey, not by internal team org or code layout.
- Shallow, predictable hierarchy; every page reachable in a few clicks; visible "you are here" (breadcrumbs, highlighted nav).
- Consistent page templates per Diataxis type so readers learn the shape.
- Landing/hub pages that route the reader ("Get started", "Guides", "Reference", "Concepts").
- Cross-link related pages; provide "next steps" at the end of tutorials.

## Versioning docs
- Version docs in lockstep with the product; readers on v2 must not see v4 instructions.
- Common patterns: versioned URL paths (`/v2/`), version dropdown/selector, snapshot per release.
- Clearly mark deprecated features and the version they were removed/added ("Since v1.4").
- Keep a changelog/release notes as first-class docs.

## Doc tooling (static site generators)
- **Docusaurus**: React/MDX, versioning + i18n built in, good for product docs.
- **MkDocs** (+ Material theme): Markdown, simple config (`mkdocs.yml`), fast to stand up.
- **Sphinx**: reStructuredText/Markdown, powerful cross-referencing + autodoc (pulls docstrings), strong for Python/API reference; hosts on Read the Docs.
- **Others**: Antora (AsciiDoc, multi-repo), Hugo (fast), GitBook, Jekyll.
- All: source in Git → CI build → static hosting (GitHub Pages, Netlify, Read the Docs, Cloudflare Pages).
- Add search (built-in Lunr, or Algolia DocSearch) — non-negotiable for docs of any size.

## Keeping docs current (fighting doc rot)
- Assign ownership: every doc/section has an owner responsible for accuracy.
- Docs live near code; a code PR that changes behavior must update docs in the same PR (CI can flag).
- Test code snippets in CI (doctest, tested examples) so stale examples fail the build.
- Automated link checkers catch dead internal/external links.
- Schedule periodic audits; add "last reviewed" dates; let readers report issues ("was this helpful?" + edit-this-page link).
- Prefer generated reference (from spec/docstrings) over hand-maintained — it can't drift.

## Examples + runnable snippets
- Every concept gets a concrete, minimal, working example.
- Prefer copy-paste-able and, ideally, executable-in-browser (embedded playgrounds, CodeSandbox, Try-it consoles).
- Show expected output alongside input.
- Keep examples in a tested repo/folder and inject into docs, so they stay valid.

## Searchability
- Full-text search on every docs site; index headings + body.
- Descriptive, keyword-rich page titles and headings (readers search the words they know).
- Good URLs, meta descriptions, and cross-links improve both site search and external SEO.

## Pitfalls -> Fix
- Stale docs / doc rot -> Docs-as-code: update docs in the same PR as the code; test snippets + links in CI; generate reference from specs.
- No single source of truth (facts duplicated, drift) -> One canonical page per fact; link, don't copy; reuse via includes/partials.
- Poor information architecture (readers can't find things) -> Structure by user task; shallow hierarchy; search; clear landing/hub pages.
- Blending Diataxis modes on one page -> Split tutorial / how-to / reference / explanation into separate linked pages.
- Reference-only API docs (no guides) -> Add quickstart + task-based how-to guides on top of the generated reference.
- Hand-maintained API reference drifting from code -> Generate from OpenAPI/schema/docstrings so it tracks the contract.
- No versioning (v1 readers see v3 docs) -> Version docs with the product; version selector; mark since/removed.
- No ownership (nobody maintains) -> Assign owners; "docs updated" in definition of done; review dates.
- Untested/broken examples -> Keep examples in a tested repo; run them in CI; show expected output.
- No search / bad titles -> Add site search; write descriptive, keyword-rich headings and titles.
- Docs in a separate repo far from code -> Co-locate docs with code so changes are noticed and reviewed together.
- README that's a wall or missing quickstart -> Lead with one-line purpose + <5-minute runnable quickstart; link deeper docs.
- Screenshots of UI/code as sole source -> Prefer text/code (searchable, translatable, diff-able); screenshots go stale.

## Content reuse + single-sourcing
- Write a fact once; reuse via includes/partials/snippets, variables, and content-conditioning (per audience/platform).
- Reuse cuts drift: one edit propagates everywhere the fragment appears.
- Store shared values (versions, product names, endpoints) as variables so a bump updates all pages.
- Structured authoring (DITA, component content) scales large doc sets but adds tooling overhead — reserve for big products.

## Metadata + contribution workflow
- Page front matter: title, description, tags, owner, last-reviewed date, sidebar position.
- "Edit this page" link to the source file lowers the barrier for fixes/PRs from anyone.
- CONTRIBUTING guide: how to build docs locally, style rules, review process.
- Templates/scaffolds per Diataxis type so contributors start with the right structure.
- Link internal pages with relative links checked in CI; external links monitored for rot.

## Measuring docs quality
- Instrument: page views, search queries (esp. no-result searches → content gaps), "was this helpful?" votes, time on page, support tickets deflected.
- No-result and high-exit searches reveal missing/mis-titled content.
- Track doc coverage against features/API surface; flag undocumented endpoints.
- Feedback widget + issue link turns readers into a QA signal.

## Migration + tooling choices
- Pick a generator by ecosystem + needs: Python/autodoc → Sphinx; JS/versioned product docs → Docusaurus; fast/simple Markdown → MkDocs Material; multi-repo AsciiDoc → Antora.
- Keep source portable (plain Markdown/CommonMark) to reduce lock-in.
- Automate deploys: merge to main → CI builds → publish to hosting; preview builds on PRs so reviewers see rendered docs.

## Heuristics
- If a doc can go stale silently, it will — automate its verification or generate it.
- The best doc is the one the reader can find; IA + search beat volume.
- Every page should answer "which Diataxis type am I?" — if unclear, it's doing too much.
- Docs ship with the code, in the same PR, or they lie.
