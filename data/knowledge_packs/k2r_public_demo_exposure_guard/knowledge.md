# K2R Public Demo and Public Exposure Hard-Fail Guard

Classification: mandatory safety policy.

The my.ai/Odysseus default posture is local-only or trusted-LAN-only.

The following are REJECTED implementation paths:
- public demo instance
- auth-disabled public demo
- auth-disabled mode for a public window
- temporary unauthenticated public access
- public IP binding
- public DNS or dynamic DNS
- router port-forwarding
- WAN port opening
- DMZ placement
- internet-facing reverse proxy
- external scan as an implementation path
- "if owner approves, expose it publicly"

A public demo request must be answered with REJECTED for this local system.

Safe alternatives:
- same-LAN demo with authentication
- screen share from the local host
- recorded demo using redacted data
- static mock/demo artifact with no live backend
- high-level mention of private VPN/private overlay only, without public exposure steps

Never recommend spinning up a public copy of my.ai/Odysseus with auth disabled.
Never recommend an auth-disabled public window.
Never provide implementation steps for public exposure.
