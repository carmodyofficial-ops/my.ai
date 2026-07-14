"""Client-facing error codes for the wearables gateway.

Internal failures are normalized into these stable codes so the mobile app can
key its recovery UX off them without parsing prose. Raise via gw_error();
the detail shape is always {"code": <CODE>, "message": <safe text>}.
"""

from fastapi import HTTPException

# Enrollment / auth
PAIRING_CODE_INVALID = "PAIRING_CODE_INVALID"
DEVICE_CREDENTIAL_REVOKED = "DEVICE_CREDENTIAL_REVOKED"
AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
FORBIDDEN_SCOPE = "FORBIDDEN_SCOPE"

# Request shape
BAD_REQUEST = "BAD_REQUEST"
PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
RATE_LIMITED = "RATE_LIMITED"
SESSION_NOT_FOUND = "SESSION_NOT_FOUND"

# Capability availability
STT_UNAVAILABLE = "STT_UNAVAILABLE"
STT_FAILED = "STT_FAILED"
TTS_UNAVAILABLE = "TTS_UNAVAILABLE"
TTS_FAILED = "TTS_FAILED"
LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
VISION_MODEL_NOT_CONFIGURED = "VISION_MODEL_NOT_CONFIGURED"
VISION_FAILED = "VISION_FAILED"

# Runtime
REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
SESSION_CANCELLED = "SESSION_CANCELLED"


def gw_error(status: int, code: str, message: str) -> HTTPException:
    """Build the gateway's uniform HTTPException. Never put secrets, raw
    prompts, or internal stack detail in `message` — it goes to the device."""
    return HTTPException(status_code=status, detail={"code": code, "message": message})
