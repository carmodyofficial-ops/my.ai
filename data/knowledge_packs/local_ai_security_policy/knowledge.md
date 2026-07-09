# Local AI Security Policy

Purpose: Preserve the local-only/private security model while allowing trusted LAN use.

Security principles:
- Local-first by default.
- LAN access may be enabled for trusted Wi-Fi users only.
- Never expose the app to the public internet without explicit owner approval.
- Never weaken authentication or session handling casually.
- Never hardcode secrets, API keys, passwords, or tokens into source.
- Never edit `.env`, private keys, secret stores, auth databases, or token files unless explicitly scoped.

Protected boundaries:
- Admin capabilities must remain admin-only.
- Guest is a low-privilege shared account.
- Guest must not use bash, local agents, privileged tools, user management, or memory management.
- Auth-disabled or internal-tool bypasses must be treated as sensitive.
- Reserved usernames and internal sentinels must not become real users.

Auth/session rules:
- Cookies should be HttpOnly.
- SameSite Lax is acceptable for local/LAN app use.
- Admin routes must enforce admin checks server-side.
- UI hiding is not security; server-side gates are required.
- 403 for Guest admin access is correct.
- 302 to login for unauthenticated root is expected.

Forbidden unsafe recommendations:
- Opening router ports to the app.
- Disabling auth for convenience.
- Giving Guest admin, bash, or agent privileges.
- Ignoring failed tests.
- Treating a passing compile as sufficient validation.
- Replacing large security files without diff review.
