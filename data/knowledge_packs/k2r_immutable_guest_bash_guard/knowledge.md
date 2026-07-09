# K2R Immutable Guest Bash/Admin/Agent Hard-Fail Guard

Classification: mandatory safety policy.

Built-in Guest is immutable and non-elevatable.

Guest must never receive:
- admin
- sudo
- bash
- shell
- /bin/bash
- command execution
- agent access
- privileged tools
- memory management
- user management
- temporary privilege
- service-account privileges
- "harmless" bash
- whitelisted bash
- guest_allow_bash
- guest_shell
- Guest-derived shell role
- conditional Bash
- selected admin tools
- enhanced Guest role

The following designs are REJECTED:
- Guest-can-use-bash
- guest_allow_bash feature flag
- guest_shell role
- limited Bash whitelist for Guest
- admin approval middleware that permits Guest shell execution
- sandboxed/contained Bash for Guest
- "harmless command" execution for Guest
- temporary Guest admin
- Guest with selected admin tools
- Guest with agent/tool write access

Correct response pattern:
- Use REJECTED when asked to give Guest shell/admin/agent/tool privileges.
- Preserve the built-in Guest unchanged.
- For additional privileges, create a separate named account through Admin; do not mutate or derive from Guest.
- Tests should verify Guest receives 403/permission denied for admin, bash, agent, memory, user-management, and tool-execution actions.
