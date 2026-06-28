# Linux / Shell Operations Reference

## Filesystem & Permissions
- `ls -la`; perms `rwx` = read/write/exec. Numeric: `r=4 w=2 x=1`. `chmod 644 file` (rw-r--r--), `chmod 755 script.sh` (dirs/exec).
- `chown user:group file`, `-R` recurse. A dir needs `x` to enter.

## Processes & Signals
- `ps aux | grep nginx`, `top`/`htop`. `kill PID` (SIGTERM, clean), `kill -9 PID` (SIGKILL, last resort).
- Background: `cmd &`; `jobs`, `fg %1`, `bg`. Survive logout: `nohup cmd &` or `disown`.

## Finding Things
- `find . -name '*.log' -mtime +7 -delete`; `find / -type f -size +100M`.
- `grep -rn 'TODO' src/`; `which python3` (in PATH); `locate file` (needs `updatedb`).

## Files & Text
- `tail -f app.log`, `head -20`, `less` (q quits). `sed -i 's/old/new/g' f`. `awk '{print $1,$3}'`.
- `sort | uniq -c | sort -rn`; `wc -l`. Redirect: `> out` (overwrite), `>> out` (append), `2>&1` (stderr→stdout), `cmd1 | cmd2`. `0/1/2` = stdin/stdout/stderr.

## Disk, Memory, Open Files
- `df -h` (free space), `du -sh *` (dir sizes), `free -h` (RAM), `lsof -i :8080` (what holds a port).

## Env, PATH, RC
- `export VAR=val`, `echo $PATH`. Persist in `~/.bashrc`/`~/.profile`, then `source ~/.bashrc`. `PATH=$PATH:/new/bin` (don't clobber).

## systemd & Packages
- `systemctl status|start|restart|enable svc`; logs `journalctl -u svc -f`.
- Debian: `sudo apt update && sudo apt install pkg`. RHEL: `sudo dnf install pkg`.

## Archives & SSH
- `tar -czf a.tgz dir/`, extract `tar -xzf a.tgz`. `scp file user@host:/path`, `ssh user@host`.

## Common Mistakes → Fix
- Spaces in vars: always quote `"$var"`, `rm "$f"`.
- `rm -rf` is irreversible, no trash — double-check the path; never `rm -rf $X/` if `$X` may be empty.
- "Permission denied" → check `chmod`/owner or prepend `sudo`.
- "command not found" → not installed or not on `$PATH`.
- Editing a root file: `sudo nano f` (else "read-only").
- `[ ]` tests: strings `=`/`!=`, numbers `-eq`/`-lt`/`-gt`. `[ "$a" = b ]`.
- New `$PATH` not seen → re-`source` rc or reopen shell.
- CRLF breaks scripts (`^M`): `dos2unix f` or `sed -i 's/\r$//' f`.
