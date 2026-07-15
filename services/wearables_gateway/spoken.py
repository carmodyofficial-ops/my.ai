"""Convert generated markdown/prose into a spoken-response representation.

Glasses users HEAR the answer, so: no markdown syntax read literally, no raw
URLs, no code blocks, bounded length with sentence-boundary truncation. The
full untransformed text still goes to the phone screen via the delta stream;
this transform only feeds TTS and the `spoken` SSE event.
"""

from __future__ import annotations

import re

DEFAULT_MAX_SPOKEN_CHARS = 2400  # ceiling on run-on TTS; ≈ 45-60 s. Only caps
# genuinely long answers — concise ones are unaffected, and the full text is
# always on the phone. Raised so thorough answers aren't cut off mid-thought.

_CODE_FENCE_RE = re.compile(r"```.*?(?:```|$)", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]{1,120})`")
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_HEADER_RE = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
_EMPHASIS_RE = re.compile(r"(\*\*|__|\*|_)(?=\S)(.+?)(?<=\S)\1")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_CITATION_RE = re.compile(r"【[^】]*】|\[\d+\]|\[\^?\d+\^?\]")
_BLOCKQUOTE_RE = re.compile(r"^\s*>\s?", re.MULTILINE)
_HRULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE)
_SENTENCE_END_RE = re.compile(r"[.!?][\"')\]]?\s")


def spoken_text(text: str, max_chars: int = DEFAULT_MAX_SPOKEN_CHARS) -> dict:
    """Return {"spoken": str, "truncated": bool}.

    `truncated` tells the client to offer a "tell me more" follow-up; the full
    text remains available on the phone.
    """
    s = text or ""

    had_code = bool(_CODE_FENCE_RE.search(s))
    s = _CODE_FENCE_RE.sub(" ", s)
    s = _INLINE_CODE_RE.sub(r"\1", s)
    s = _MD_IMAGE_RE.sub(lambda m: m.group(1) or "", s)
    s = _MD_LINK_RE.sub(r"\1", s)
    had_url = bool(_URL_RE.search(s))
    s = _URL_RE.sub("", s)
    had_table = bool(_TABLE_ROW_RE.search(s))
    s = _TABLE_ROW_RE.sub(" ", s)
    s = _CITATION_RE.sub("", s)
    s = _HEADER_RE.sub("", s)
    s = _BULLET_RE.sub("", s)
    s = _BLOCKQUOTE_RE.sub("", s)
    s = _HRULE_RE.sub(" ", s)
    # Run emphasis twice: bold-italic nests (***x***) leave one marker behind.
    s = _EMPHASIS_RE.sub(r"\2", s)
    s = _EMPHASIS_RE.sub(r"\2", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", " ", s).strip()

    notices = []
    if had_code:
        notices.append("I've put the code on your phone.")
    if had_table:
        notices.append("There's a table with details on your phone.")
    if had_url and not s:
        notices.append("I've sent a link to your phone.")

    truncated = False
    if len(s) > max_chars:
        cut = s[:max_chars]
        # Prefer ending on a sentence boundary in the back half of the budget.
        last_end = None
        for m in _SENTENCE_END_RE.finditer(cut):
            last_end = m.end()
        if last_end and last_end > max_chars // 2:
            cut = cut[:last_end]
        s = cut.rstrip()
        truncated = True

    if notices:
        s = (s + " " if s else "") + " ".join(notices)
    if truncated:
        s += " Want to hear more?"

    return {"spoken": s.strip(), "truncated": truncated}


def last_sentence_end(text: str, start: int = 0) -> int:
    """Index into `text` just past the last COMPLETE sentence at/after `start`
    (or `start` if none). Lets /respond stream spoken sentences incrementally so
    the first sentence's TTS starts while the rest of the answer is still
    generating, instead of waiting for the whole reply."""
    end = start
    for m in _SENTENCE_END_RE.finditer(text, start):
        end = m.end()
    return end
