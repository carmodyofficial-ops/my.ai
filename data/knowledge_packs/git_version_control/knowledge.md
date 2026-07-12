# Git Reference

## Object model
- Four objects, content-addressed by SHA-1/256: **blob** (file bytes), **tree** (dir listing → blobs/trees), **commit** (tree + parent(s) + author/msg), **tag** (annotated).
- **HEAD** = ref to current branch (or a raw SHA when detached). A **branch** is just a movable pointer (a file in `.git/refs/heads`) to a commit. Commits are immutable; "changing" one makes a new SHA.
- **Index/staging** (`.git/index`) is the proposed next commit. Three trees interplay: HEAD (last commit) ↔ index (staged) ↔ working tree (files on disk).

## Branching & integration
- `git switch -c feat/x` off `main`; keep branches short-lived, one topic. Push `git push -u origin feat/x`.
- **Merge** creates a merge commit joining histories (non-destructive, preserves context). Fast-forward when no divergence (just moves pointer); force a merge commit with `--no-ff`.
- **Rebase** replays your commits onto a new base → linear history but **new SHAs**. Use to tidy *local, unpushed* work: `git rebase main`.
- **NEVER rebase/amend shared, pushed history** — everyone else's commits now reference SHAs that no longer exist.

## Interactive rebase
- `git rebase -i HEAD~4` → per-line: `pick`, `reword` (edit msg), `edit` (stop to amend), `squash` (merge + combine msgs), `fixup` (merge, drop msg), `drop`, or reorder lines. `git commit --fixup=<sha>` + `rebase -i --autosquash` automates fixups.

## Cherry-pick
- `git cherry-pick <sha>` copies one commit's diff onto HEAD (new SHA). Range `A^..B`; `-n` stage without committing; `-x` records origin.

## Reset vs revert vs restore
- **`git reset`** moves the branch pointer (rewrites history):
  - `--soft HEAD~1` keep changes **staged**.
  - `--mixed HEAD~1` (default) keep changes in working tree, **unstaged**.
  - `--hard HEAD~1` **discard** working tree + index — uncommitted work is gone.
- **`git revert <sha>`** makes a new inverse commit — safe undo of a *pushed* commit; use on shared branches instead of reset.
- **`git restore`** touches files, not history: `--staged <f>` unstage (index→match HEAD), `<f>` discard working edits (from index), `--source=<sha> <f>` pull an old version.

## Stash
- `git stash [push -m msg]` shelves tracked changes; `-u` includes untracked. `git stash pop` (apply+drop) / `apply` (keep). `git stash list`, `stash show -p`, `stash branch <name>`.

## Reflog (recovery net)
- `git reflog` logs every HEAD move (also `reflog show <branch>`). Recover a "lost" commit/branch/bad reset: `git reset --hard <sha>` or `git switch -c rescue <sha>`. Entries expire (~90d default) and are local-only.

## Bisect
- `git bisect start; git bisect bad; git bisect good <old-sha>` → git checks out midpoints; mark `good`/`bad` each step (binary search) to find the first bad commit. Automate: `git bisect run <test-cmd>` (exit 0=good, non-0=bad). `git bisect reset` when done.

## Worktrees
- `git worktree add ../wt-hotfix hotfix` = second working directory sharing one `.git`, checked out to a different branch — parallel work without stashing/cloning. `git worktree list` / `remove`. A branch can't be checked out in two worktrees at once.

## Submodules
- `git submodule add <url> path` pins a nested repo at a specific commit (recorded in the superproject). Clone with `--recurse-submodules` or `git submodule update --init --recursive`. Updating = enter submodule, checkout, then commit the new pointer in the parent. Common pain: forgetting to init, or committing a moved pointer nobody else fetched.

## Hooks
- Scripts in `.git/hooks` (local, not versioned): `pre-commit` (lint/format, non-zero aborts), `commit-msg` (validate message), `pre-push`, `post-merge`. Share via a tracked dir + `core.hooksPath` or a manager (pre-commit, husky). `--no-verify` bypasses client hooks.

## Conflict resolution
- Merge/rebase stops; markers `<<<<<<< ours` / `=======` / `>>>>>>> theirs`. Edit to the desired result, remove all markers, `git add <file>`, then `git rebase --continue` / `git merge --continue` (or `--abort`). `git checkout --ours/--theirs <f>` takes one side wholesale. `rerere` remembers resolutions to replay.

## Tags
- Lightweight (`git tag v1`) vs annotated (`git tag -a v1.0 -m msg`, has tagger/date, use for releases). Not pushed by default: `git push origin v1.0` or `--tags`. Moving a published tag is hostile — cut a new one.

## History rewriting (danger)
- `git commit --amend` replaces the last commit (new SHA). `git filter-repo` (preferred over `filter-branch`) rewrites bulk history to purge files/secrets — rewrites *every* downstream SHA; requires force-push and everyone re-cloning.

## Recovery recipes
- Undo last commit, keep work staged: `git reset --soft HEAD~1`.
- Unstage: `git restore --staged <f>`. Discard edits: `git restore <f>`.
- Recover deleted branch: find SHA in `git reflog`, `git switch -c <name> <sha>`.
- Recover after bad `reset --hard`: `git reflog` → `git reset --hard <sha>`.

## Gotchas → Fix
- Force-push clobbers teammates' commits → use `git push --force-with-lease` (aborts if remote moved), never bare `--force`.
- **Detached HEAD**: commits made here orphan on next checkout → branch first `git switch -c keep` (reflog can still rescue within expiry).
- Rebasing/amending public history breaks everyone's clones → revert instead on shared branches.
- Committed secrets live in history forever → rotate the credential immediately; a later delete/`.gitignore` does NOT erase past commits (use `filter-repo`).
- `.gitignore` only ignores **untracked** paths; already-tracked files keep tracking → `git rm --cached <f>` then commit.
- `git reset --hard` / `git checkout .` silently drop uncommitted work with no reflog entry → stash or commit first.
- Merge vs rebase confusion: rebase for local cleanup, merge for shared integration; don't rebase what others pulled.
- `git pull` = fetch + merge by default → surprise merge commits; `git pull --rebase` or set `pull.rebase`.
