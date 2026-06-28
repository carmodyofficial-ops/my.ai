---
name: git-workflow
description: "How to work with git safely: branch, commit in logical units, integrate with merge/rebase correctly, resolve conflicts, and recover from mistakes with reflog/reset/revert without losing work."
version: 1.0.0
category: Coding
tags: [git, commit, branch, merge, rebase, conflict, revert, reset, stash, reflog, undo, version control, push, pull request]
platforms: [local]
status: published
confidence: 1.0
source: user
owner: admin
created: "2026-06-26T00:00:00Z"
---

## When to Use

Use for any git operation beyond a trivial commit — branching, integrating changes, resolving conflicts, undoing a mistake, or recovering "lost" work.

## Procedure

1. Branch per topic: `git switch -c feat/x` off the main branch; keep it short-lived and focused on one change.
2. Commit in logical units: stage related changes together, write a clear imperative message ("Add X", "Fix Y"). One concern per commit — don't bundle a refactor with a feature.
3. Check before you commit: `git status` + `git diff --staged` to confirm exactly what's going in (and that no secret/.env slipped in).
4. Integrate correctly: rebase to tidy LOCAL history before pushing (`git rebase main`), merge/squash-merge into shared branches. NEVER rebase or amend history that's already been pushed/shared.
5. Resolve conflicts deliberately: edit the `<<<</====/>>>>` markers to the intended result, delete the markers, `git add` the file, then `--continue`. Abort with `--abort` if it's a mess.
6. Undo safely by what you want to keep: `reset --soft HEAD~1` (keep staged), `restore --staged <f>` (unstage), `restore <f>` (discard edits), `revert <sha>` (undo a PUSHED commit via an inverse commit). Use `reflog` to recover a "lost" commit/branch.

## Pitfalls

- `git push --force` clobbers teammates — use `--force-with-lease`.
- `reset --hard` discards uncommitted work irreversibly — be sure first.
- Rebasing/amending pushed history breaks everyone's clones.
- Committing a secret — it persists in history forever; rotate the key (deleting later doesn't erase it).
- Detached HEAD: commits orphan — branch first.
- A panicked "I lost my work" — almost always recoverable via `git reflog`.

## Verification

- The commit contains only the intended files (checked the diff), with a clear message.
- History integration used the right tool (rebase local, merge shared), no force-push to shared.
- After an undo, the tree is in the intended state and nothing was silently lost.
