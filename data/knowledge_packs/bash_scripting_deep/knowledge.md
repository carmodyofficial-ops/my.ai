# Robust Bash Reference

## Strict mode (top of every script)
```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'   # optional: safer default splitting
```
- `-e` exit on any unhandled non-zero. `-u` error on unset var reference. `-o pipefail` a pipeline fails if *any* stage fails (default: only exit status of last stage matters).
- `-e` is fragile: it is disabled inside command that is the condition of `if`/`while`/`&&`/`||`, negated with `!`, or in a `$( )` subshell whose result is unused. Don't rely on `-e` alone — check critical commands explicitly.

## Quote everything
- `"$var"`, `"$@"`, `"${arr[@]}"`. Unquoted = word-splitting on `IFS` + glob expansion. `rm $f` breaks on spaces/globs; `rm "$f"` safe.
- Forward args with `"$@"` (expands to separate quoted words), NEVER `$*` (joins into one word) or bare `$@`.
- Command substitution results also split unless quoted: `x="$(cmd)"`.

## Parameter expansion
- `${var:-def}` value or def if unset/empty; `${var-def}` only if unset. `${var:=def}` assign default. `${var:?msg}` abort with msg if unset. `${var:+alt}` alt if set.
- Strip: `${var#pre}` shortest leading, `${var##*/}` longest (basename); `${var%.txt}` shortest trailing, `${var%%.*}` longest (strip all ext).
- Replace: `${var/a/b}` first, `${var//a/b}` all, `${var/#a/b}` anchor-start, `${var/%a/b}` anchor-end.
- Substring: `${var:0:3}`, `${var: -3}` (note space, last 3). Length `${#var}`. Case `${var^^}` upper, `${var,,}` lower. Indirect `${!name}`.

## Arrays
```bash
declare -a arr=(a b "c d")     # indexed
arr+=(e)                        # append
for x in "${arr[@]}"; do :; done
echo "${#arr[@]}"               # count
echo "${arr[@]:1:2}"            # slice
declare -A m=([k]=v); echo "${m[k]}"   # associative (bash 4+)
for k in "${!m[@]}"; do echo "$k=${m[$k]}"; done   # keys
```
`${arr[@]}` = separate words; `${arr[*]}` = single word joined by first IFS char. Unset `arr` alone = only element 0.

## Conditionals & tests
- Use `[[ ]]` not `[ ]`: no word-splitting/glob on unquoted vars, supports `&&` `||` `<` `>`, `=~` regex, `-n`/`-z`. `[ ]` is a program with quoting traps.
- `[[ $x == pat* ]]` glob match (unquoted RHS); `[[ "$x" == "$lit" ]]` literal (quoted RHS). `[[ $s =~ ^[0-9]+$ ]]` regex; captures in `${BASH_REMATCH[@]}`; do NOT quote the regex.
- Arithmetic: `(( x > 3 ))`, `(( count++ ))`, `n=$(( a + b ))`.

## Loops & reading
```bash
while IFS= read -r line; do printf '%s\n' "$line"; done < file
mapfile -t lines < file          # slurp file into array (bash 4+)
for f in ./*.txt; do [[ -e $f ]] || continue; done   # guard empty glob
find . -name '*.log' -print0 | while IFS= read -r -d '' f; do :; done
```
`IFS=` keeps leading/trailing whitespace; `-r` stops backslash mangling. Set `shopt -s nullglob` so unmatched globs vanish instead of staying literal.

## Functions & locals
```bash
foo() {
  local x="$1" out              # local ALWAYS to avoid leaking globals
  out=$(some cmd) || return 1
  printf '%s\n' "$out"          # "return" data via stdout
}
result=$(foo arg)               # capture
foo arg; rc=$?                  # status via exit code (0-255)
```
`local x=$(cmd)` masks cmd's exit status (local's succeeds) — split into two lines if you need `$?`.

## getopts
```bash
verbose=0
while getopts ":f:v" o; do case $o in
  f) file=$OPTARG ;;
  v) verbose=1 ;;
  :) echo "-$OPTARG needs arg" >&2; exit 2 ;;
  \?) echo "bad -$OPTARG" >&2; exit 2 ;;
esac; done
shift $((OPTIND-1))             # drop parsed opts, "$@" now = positionals
```
Leading `:` in optstring = silent errors (you handle `:`/`\?`). Only single-char flags.

## Process substitution / here-docs
```bash
diff <(sort a) <(sort b)        # feed cmd output as a file
while read -r l; do :; done < <(cmd)   # avoid subshell var loss (see gotchas)
cat <<'EOF'                     # quoted delimiter = NO expansion
literal $x $(cmd)
EOF
cat <<EOF                       # unquoted = expands
value is $x
EOF
grep foo <<<"$var"              # here-string
```

## Redirection & streams
- `>` truncate, `>>` append, `2>` stderr, `&>file` / `>file 2>&1` both (order matters: `2>&1` must follow the stdout redirect). `2>&1 >file` sends stderr to the *old* stdout (terminal). `>/dev/null 2>&1` silence all.
- `cmd <file` stdin; `n<>file` open rw on fd n. `exec 3>log` opens a persistent fd; `echo x >&3`; `exec 3>&-` close.
- `printf '%s\n' "$x"` over `echo` (portable, no flag mangling). `printf -v var '%d' "$n"` writes into a variable.

## Arithmetic & strings
- `(( n = a * b + 1 ))`, `(( x++ ))`, `res=$(( 2**10 ))`. Ternary `(( a>b ? a : b ))`. Base: `$(( 16#ff ))`, `$(( 2#1010 ))`.
- `$RANDOM` 0–32767. Compare numerics with `-eq -ne -lt -le -gt -ge` in `[[ ]]`, or `(( ))`.

## Traps, signals & cleanup
```bash
tmp=$(mktemp)
cleanup() { rm -f "$tmp"; }
trap cleanup EXIT               # runs on any exit
trap 'echo "err line $LINENO" >&2' ERR
```
`EXIT` fires once on normal or error exit. `trap 'kill 0' INT TERM` to also tear down children. Set traps before creating the resource. Exit-code convention: 0 ok, 1 general, 2 misuse, 126 not executable, 127 not found, 128+N killed by signal N (130 = Ctrl-C/SIGINT).

## Gotchas → Fix
- Unquoted `$var` with spaces/globs → splits/expands → always `"$var"`.
- `cmd | while read; do v=x; done` runs the loop in a subshell → `$v` lost after → use `while ...; do; done < <(cmd)` or `mapfile`.
- `set -e` not triggering (subshell, `||`, `if`-condition, last-in-pipe) → add `pipefail`, check `$?` explicitly, or `cmd || { echo fail; exit 1; }`.
- `[ $x = y ]` errors when `$x` empty/has spaces → `[[ "$x" == y ]]`.
- `local v=$(cmd)` hides cmd failure → declare then assign on separate lines.
- Empty glob stays literal (`*.txt` passed as text) → `shopt -s nullglob` or guard `[[ -e $f ]]`.
- Parsing `ls` output → breaks on spaces/newlines → use globs or `find -print0 | xargs -0`.
- `$?` resets every command → capture immediately: `rc=$?`.
- Reading changed `IFS` leaks to rest of script → scope it: `IFS=, read -ra parts <<<"$line"`.
- `echo` mangles `-n`/backslashes/leading `-` → prefer `printf '%s\n' "$x"`.
- `cd "$d"` unchecked then destructive cmd → `cd "$d" || exit 1`.
- Comparing numbers with `<`/`>` in `[[ ]]` does string compare → use `(( a < b ))`.
