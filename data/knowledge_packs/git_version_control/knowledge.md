# Git Reference

## Branching
- `git switch -c feat/x` off `main`. Keep branches short-lived; one topic each.
- Push: `git push -u origin feat/x`. Open PR; merge into `main`.

## Merge vs Rebase
- **Rebase** to clean *local* history before pushing: `git rebase main`.
- **NEVER rebase shared/pushed history** — it rewrites SHAs others depend on.
- Merge (or squash-merge) to integrate into shared branches.

## Interactive Rebase
- `git rebase -i HEAD~4` → mark `squash`/`fixup` (combine), `reword` (edit msg), `drop`, or reorder lines.

## Conflicts
- Markers `<<<<<<<` / `=======` / `>>>>>>>`. Edit to resolve, delete markers.
- `git add <file>` then `git rebase --continue` (or `git merge --continue`). Abort: `--abort`.

## Cherry-pick
- `git cherry-pick <sha>` copies one commit here. Range: `A^..B`.

## Reset (moves HEAD)
- `--soft HEAD~1`: keep changes **staged**.
- `--mixed HEAD~1` (default): keep changes in working tree, unstaged.
- `--hard HEAD~1`: **DISCARD everything** — unrecoverable for uncommitted work.

## Revert
- `git revert <sha>`: safe undo of a *pushed* commit via a new inverse commit. Use on shared branches instead of reset.

## Stash
- `git stash` / `git stash pop`. List: `git stash list`.

## Reflog (recover "lost" commits)
- `git reflog` shows every HEAD move. Recover: `git reset --hard <sha>` or `git switch -c rescue <sha>`.

## Bisect
- `git bisect start; git bisect bad; git bisect good <sha>`; test each step, `good`/`bad`; `git bisect reset`.

## Misc
- Amend last commit: `git commit --amend` (rewrites SHA — don't if pushed).
- `.gitignore` excludes untracked paths; already-tracked files need `git rm --cached`.
- Tags: `git tag -a v1.0 -m msg; git push --tags`.

## Recovery Recipes
- Undo last commit, keep work: `git reset --soft HEAD~1`.
- Unstage: `git restore --staged <file>`.
- Discard local edits: `git restore <file>`.
- Deleted branch: find SHA in `git reflog`, `git switch -c <name> <sha>`.

## Gotchas
- Force-push clobbers teammates — use `git push --force-with-lease`, never bare `--force`.
- Detached HEAD: commits orphan on checkout — branch first: `git switch -c keep`.
- Rebasing/amending public history breaks everyone's clones.
- Committed secrets persist in history forever — rotate the key; a later delete doesn't erase it.
