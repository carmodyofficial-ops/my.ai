# Regex Reference

## Anchors
- `^` start, `$` end (of string; per-line with `m` flag). `\b` word boundary, `\B` non-boundary.
- Always anchor full-match validation: `^\d{4}$` not `\d{4}`.

## Character classes
- `[a-z]` range, `[^0-9]` negate, `[A-Za-z0-9_]`.
- `\d \w \s` = digit/word/whitespace; `\D \W \S` negate. Inside `[]`, most metachars are literal (escape `]` `\` `^` `-`).

## Quantifiers — greedy vs lazy
- `*` 0+, `+` 1+, `?` 0/1, `{2,5}` range, `{3}` exact.
- Greedy `.*` grabs max; lazy `.*?` grabs min. For `<(.+?)>` use lazy to stop at first `>`.
- Prefer negated class over lazy: `"[^"]*"` beats `".*?"`.

## Groups & alternation
- Capturing `(ab)`, non-capturing `(?:ab)`, named `(?P<year>\d{4})`.
- Alternation `cat|dog`; bound it: `^(cat|dog)$`.
- Backref `(['"]).*?\1` matches matching quotes.

## Lookaround
- `(?=...)` ahead, `(?!...)` neg-ahead, `(?<=...)` behind, `(?<!...)` neg-behind. Zero-width.
- Password-ish: `(?=.*\d)(?=.*[a-z]).{8,}`.

## Flags
`i` ignore-case, `m` multiline (`^$` per line), `s` DOTALL (`.` matches `\n`), `x` verbose. Python: `re.compile(p, re.I|re.S)` or inline `(?i)`.

## Escaping
Escape `. ^ $ * + ? ( ) [ ] { } | \ /`. Use `re.escape(user_input)` for literals.

## Patterns
- Trim: `^\s+|\s+$`.
- Split CSV-ish: `re.split(r'\s*,\s*', s)`.
- key=value: `(?P<k>\w+)=(?P<v>[^;]+)`.
- URL-ish: `https?://[^\s/]+\S*`.
- Email (rough only): `[^@\s]+@[^@\s]+\.[^@\s]+` — do NOT fully validate email by regex; check via sending.

## Gotchas
- ReDoS: avoid nested quantifiers `(a+)+`, `(.*)*`, overlapping alternation on long input. Use atomic/possessive or non-regex.
- `.` excludes `\n` without `s`. Greedy `.*` spans lines/tags — narrow it.
- Forgetting to escape `.` `(` `[` matches wrong chars.
- Unicode: `\w` may miss accents; use `re.UNICODE` (default in Py3) or `\p{L}` (regex module).
- Nested/structured data (HTML, JSON, code) is NOT regular — use a parser, not regex.
