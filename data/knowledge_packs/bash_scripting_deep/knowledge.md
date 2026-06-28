# Robust Bash Reference

## Strict mode (top of every script)
```bash
set -euo pipefail
```
- `-e` exit on any unhandled error. `-u` error on unset var. `-o pipefail` a pipeline fails if *any* stage fails (else only last matters).

## Quote everything
`"$var"`, `"$@"`, `"${arr[@]}"`. Unquoted = word-splitting + glob expansion. `rm $f` breaks on spaces; `rm "$f"` is safe. Use `"$@"` (never `$*`) to forward args.

## Parameter expansion
- `${var:-def}` default if unset/empty
- `${var:?msg}` abort if unset
- `${var%.txt}` strip suffix · `${var#pre}` strip prefix (`%%`/`##` greedy)
- `${var//a/b}` replace all · `${#var}` length · `${var:0:3}` substring

## Arrays
```bash
declare -a arr=(a b "c d")
for x in "${arr[@]}"; do echo "$x"; done
echo "${#arr[@]}"   # count
```

## Functions
```bash
foo() { local x="$1"; echo "result"; }   # local always
out=$(foo arg)        # return value via echo
foo arg || return 1   # status via return
```

## Tests / loops
Use `[[ ]]` not `[ ]` (no splitting, supports `&&`, `=~`, `<`).
```bash
[[ -f "$f" && -n "$x" ]]
[[ "$s" =~ ^[0-9]+$ ]]
while IFS= read -r line; do echo "$line"; done < file
mapfile -t lines < file   # read file into array
```
Command sub: `$(cmd)` not backticks. `cd "$d" || exit 1` always check.

## Traps / cleanup
```bash
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
```

## getopts
```bash
while getopts "f:v" o; do case $o in
  f) file=$OPTARG;; v) verbose=1;; *) exit 1;; esac
done
```

## Here-doc / string
```bash
cat <<'EOF'   # quoted EOF = no expansion
literal $x
EOF
grep x <<<"$var"
```

## Gotchas
- `set -e` ignores: subshells, `cmd || true`, last in pipe (use pipefail), `if`/`&&` conditions.
- `cmd | while read; do v=x; done` runs in subshell — `$v` lost after. Use `< <(cmd)` or `mapfile`.
- Never parse `ls`; use globs or `find -print0 | xargs -0`.
- Check `$?` immediately; it resets each command.
- `[ $x = y ]` fails if `$x` empty/spaced — quote: `[[ "$x" == y ]]`.
