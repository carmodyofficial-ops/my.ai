# Regex Reference

## Anchors & boundaries
- `^` start, `$` end. Of the whole string by default; per-line with `m`/MULTILINE flag. `\A`/`\z` (`\Z`) force absolute string start/end regardless of `m` (PCRE/Python).
- `\b` word boundary, `\B` non-boundary. `\b` sits between `\w` and non-`\w`.
- Always anchor a full-match validation: `^\d{4}$`, not `\d{4}` (latter matches any 4 digits anywhere).

## Character classes
- `[a-z]` range, `[^0-9]` negate, `[A-Za-z0-9_]`. Inside `[]` most metachars are literal; escape/position `]` `\` `^` `-` (put `-` first/last, `^` not first).
- `\d \w \s` = digit/word/whitespace; `\D \W \S` negate. `\w` = `[A-Za-z0-9_]` in ASCII mode.
- `.` = any char except `\n` (unless `s`/DOTALL). POSIX classes `[[:alpha:]]`, `[[:digit:]]`.

## Quantifiers — greedy / lazy / possessive
- `*` 0+, `+` 1+, `?` 0/1, `{2,5}` range, `{3}` exact, `{2,}` 2+.
- Greedy (default) grabs max then backtracks; lazy `*?` `+?` `??` grabs min then expands. `<(.+?)>` stops at first `>`.
- **Prefer a negated class over lazy**: `"[^"]*"` beats `".*?"` — no backtracking, faster, clearer.
- Possessive `*+`/`++` and atomic groups `(?>...)` never give back — kill backtracking (PCRE/Java, not JS/Python `re`; Python `regex` module has them).

## Groups, backrefs, alternation
- Capturing `(ab)` → `\1`/`$1`; non-capturing `(?:ab)` when you only need grouping (faster, no capture slot).
- Named: `(?P<year>\d{4})` (Python), `(?<year>\d{4})` (PCRE/JS/.NET). Backref `\k<year>` / `(?P=year)`.
- Backref `(['"]).*?\1` matches balanced quote chars.
- Alternation `cat|dog` is low precedence — bound it: `^(cat|dog)$`, not `^cat|dog$` (that's `^cat` OR `dog$`). Order matters in NFA engines: first alternative that matches wins (leftmost), so put longer/more-specific first.

## Lookaround (zero-width)
- `(?=...)` lookahead, `(?!...)` neg-lookahead, `(?<=...)` lookbehind, `(?<!...)` neg-lookbehind.
- Consume nothing → chain for AND conditions: `(?=.*\d)(?=.*[a-z]).{8,}` (has digit AND lowercase, ≥8).
- Lookbehind must be fixed-width in most flavors (JS allows variable; PCRE/Python `re` fixed; `regex` module variable).

## Flavors
- **PCRE** (PHP, nginx, `grep -P`): full features — atomic, possessive, recursion, `\K`.
- **POSIX** ERE (`grep -E`, `sed -E`): no `\d`/`\w` (use `[[:digit:]]`), no lazy, no lookaround, longest-match semantics.
- **JS**: no `\A`/`\z`, no inline flags `(?i)`, no atomic groups; has named groups, variable lookbehind (ES2018+), `d` indices flag, `u`/`v` unicode.
- **Python `re`**: `(?P<name>)`, no possessive/atomic, fixed lookbehind. The third-party `regex` module adds them + `\p{}`.

## Flags
`i` ignore-case, `m` multiline (`^$` per line), `s`/DOTALL (`.` matches `\n`), `x`/verbose (ignore whitespace + `#` comments), `g` global (JS/sed — find all), `u` unicode. Python: `re.compile(p, re.I|re.S)` or inline `(?is)` at pattern start; scoped `(?i:...)`.

## Unicode
- `\w`/`\d`/`\b` are ASCII-only unless unicode mode. Python 3 `str` patterns are unicode by default; pass `re.ASCII` to restrict. JS needs `u` flag for `\p{}`.
- `\p{L}` (letter), `\p{N}`, `\p{Lu}`, `\p{Script=Greek}` in PCRE/JS(`u`)/`regex` module — matches accented/non-Latin letters `\w` misses.
- Beware combining chars/emoji: `.` matches one code point, not one grapheme; normalize (NFC) before matching.

## Match / search / substitute
- Python: `re.match` anchors at start (not end), `re.fullmatch` whole string, `re.search` anywhere, `re.findall` (returns groups if any), `re.finditer` (match objects), `re.sub(pat, repl, s)`.
- Substitution refs: `$1`/`\1` insert group; `\g<name>` named (Python); `$0`/`\0` whole match. `re.sub` `repl` can be a function `lambda m: ...` for computed replacement. Escape a literal `$`/`\` in replacement.
- JS: `str.replace(re, '$1')`, `replaceAll`, `matchAll` (needs `g`), `.test()`. `$&` whole match, `$<name>` named.
- `sed -E 's/pat/repl/g'` uses `\1` and `&` for whole match.

## Extra constructs
- Inline flag scoping: `(?i:abc)` case-insensitive only for that group; `(?-i:...)` turns it off (PCRE/Java).
- Conditionals `(?(1)yes|no)` — match `yes` if group 1 participated (PCRE/.NET/`regex`).
- `\K` (PCRE) resets match start — keeps a lookbehind-like prefix out of the result without fixed-width limits.
- Verbose mode `x`/`(?x)`: whitespace ignored, `#` starts a comment — document complex patterns; escape a literal space as `\ ` or `[ ]`.

## Common patterns (with caveats)
- Trim: `^\s+|\s+$` (with `g`/`m`).
- Split on commas w/ spaces: `\s*,\s*`.
- key=value: `(?P<k>\w+)=(?P<v>[^;]+)`.
- URL-ish (not RFC): `https?://[^\s/]+\S*`.
- Email (rough only): `[^@\s]+@[^@\s]+\.[^@\s]+` — do NOT try to fully validate email with regex; verify by sending.

## Gotchas → Fix
- **Catastrophic backtracking / ReDoS**: nested/overlapping quantifiers `(a+)+`, `(.*)*`, `(a|a)*`, `\s+$` on long lines → exponential time → rewrite with negated classes, anchor tightly, use atomic/possessive, or a non-regex parser; cap input length.
- Greedy `.*` overmatches across delimiters/lines/tags → use `[^delim]*` or lazy `.*?` + anchor.
- `.` not matching `\n` surprises multi-line input → add `s`/DOTALL or use `[\s\S]`.
- Unanchored validation matches substrings (`\d{4}` in `abc12345`) → wrap in `^...$`.
- Forgetting to escape `.` `(` `[` `+` `?` `$` `^` `*` `|` `\` → matches wrong chars → `re.escape()` / `\Q...\E` for literals.
- Alternation without grouping binds wider than expected → parenthesize.
- `$` also matches before a trailing `\n` in many engines → use `\z` for strict end.
- `\w`/`\b` missing accented letters → enable unicode / use `\p{L}`.
- Parsing HTML/JSON/nested/balanced structures with regex → they aren't regular → use a real parser.
- Reusing a `g`-flagged JS regex object carries `lastIndex` state across `.test()` calls → recreate or reset `lastIndex`.
