# Auth and Guest Access Model

Purpose: Preserve the K2L authentication design.

Admin:
- Existing Admin login remains privileged.
- Admin controls users, settings, integrations, and privileged operations.
- Admin-only endpoints must remain server-enforced.

Guest:
- User-facing username: `Guest`
- Password: `Guest123`
- Normalized username: `guest`
- Role: low-privilege shared LAN guest.
- is_admin: false

Guest privileges:
- can_use_agent: false
- can_use_bash: false
- can_manage_memory: false
- can_use_browser: true
- can_use_documents: true
- can_use_research: true
- can_generate_images: true

Guest protections:
- Cannot be manually created over the built-in account.
- Cannot be deleted.
- Cannot be renamed.
- Cannot be renamed into.
- Cannot be promoted to admin.
- Cannot have privileges modified.
- Cannot change password.
- Cannot change 2FA.
- Must be blocked from `/api/auth/users`.

K2L validation:
- Targeted mounted-host tests passed: 50 passed.
- Live Guest login passed.
- Guest `/api/auth/status` returned authenticated true, username guest, is_admin false.
- Guest `/api/auth/users` returned HTTP 403.

Relevant files:
- `core/auth.py`
- `routes/auth_routes.py`
- `static/login.html`
- `tests/test_builtin_guest_auth.py`
- `data/projectforge_sme/coding/reports/k2l_guest_auth_live_smoke_status.json`
