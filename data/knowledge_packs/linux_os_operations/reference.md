# Linux / Shell Operations Reference

## Filesystem & Permissions
- `ls -la`: cols = perms, links, owner, group, size, mtime. Type char: `-` file, `d` dir, `l` symlink, `b`/`c` device, `s` socket, `p` fifo.
- Perms `rwx` per owner/group/other. Numeric: `r=4 w=2 x=1`. `chmod 644 file` (rw-r--r--), `chmod 755 script` (rwxr-xr-x), `chmod 600 key` (owner-only). Symbolic: `chmod u+x,go-w f`, `chmod -R g+rX dir` (`X` = dir/already-exec only).
- `chown user:group f`, `chgrp grp f`, `-R` recurse. Dir needs `x` to enter/traverse, `r` to list names, `w`+`x` to create/delete entries. Deleting a file needs `w` on the *dir*, not the file.
- Special bits: **SUID** `chmod u+s` (4xxx) runs as file owner (e.g. `passwd`); **SGID** `chmod g+s` (2xxx) on dir → new files inherit dir group; **sticky** `chmod +t` (1xxx) on `/tmp` → only owner deletes their files. Find SUID: `find / -perm -4000 -type f 2>/dev/null`.
- `umask` masks default perms: `022`→ new files 644, dirs 755. `umask 077` = private. Set in `~/.bashrc`.
- ACLs beyond ugo: `getfacl f`, `setfacl -m u:alice:rw f`. Symlinks: `ln -s target link`; hard link `ln target link` (same inode). Attrs: `chattr +i f` (immutable, even root can't edit until `-i`), `lsattr`.

## Processes, Signals, Priority
- `ps aux` (BSD) / `ps -ef` (System V); `ps -eo pid,ppid,%cpu,%mem,stat,cmd --sort=-%cpu`. `pgrep -f nginx`, `pkill -f pattern`. `top`/`htop` (`P` cpu, `M` mem sort). STAT: `R` run, `S` sleep, `D` uninterruptible (I/O — can't kill), `Z` zombie, `T` stopped, `+` foreground.
- Signals: `kill PID` = SIGTERM(15) clean; `kill -9` = SIGKILL (uncatchable, last resort, no cleanup); `kill -HUP` (1) reload config; `kill -STOP`/`-CONT` pause/resume; `kill -INT` (2) = Ctrl-C; `kill -QUIT`. `kill -l` lists. `kill -9 -PID` (negative) → whole process group.
- Priority: `nice -n 10 cmd` (lower = higher prio, -20..19), `renice -n 5 -p PID`. I/O: `ionice -c3 cmd` (idle class).
- Jobs: `cmd &`, `jobs`, `fg %1`, `bg %1`, Ctrl-Z=SIGTSTP. Survive logout: `nohup cmd &`, `disown %1`, or run under `tmux`/`screen`. `&` alone dies on SIGHUP.

## systemd & journald
- `systemctl status|start|stop|restart|reload svc`; `enable --now svc` (start + boot), `disable`, `mask` (block entirely). `systemctl daemon-reload` after editing units. `is-active`, `is-enabled`, `list-units --failed`.
- Unit files: `/etc/systemd/system/*.service` (admin) override `/lib/systemd/system/*`. Drop-ins: `systemctl edit svc` → `/etc/systemd/system/svc.d/override.conf`. Key `[Service]`: `ExecStart=`, `Restart=on-failure`, `User=`, `EnvironmentFile=`, `WorkingDirectory=`. `[Unit] After=`/`Requires=` ordering; `[Install] WantedBy=multi-user.target`.
- Logs: `journalctl -u svc -f` (follow), `-e` (end), `--since "10 min ago"`, `-p err` (priority), `-b` (this boot), `-k` (kernel), `--disk-usage`, `--vacuum-time=7d`. Persist logs: `/var/log/journal` must exist. Timers replace cron: `systemctl list-timers`.

## Text Tools
- `grep -rniE 'foo|bar' src/` (recursive, ignore-case, num, ext-regex); `-l` names only, `-c` count, `-v` invert, `-o` matched part, `-A/-B/-C N` context, `--include='*.py'`. `rg` (ripgrep) faster if present.
- `sed -i 's/old/new/g' f` (in-place; `-i.bak` backups); `sed -n '5,10p' f`; `sed '/pat/d'` delete lines.
- `awk '{print $1,$3}'`, `awk -F: '$3>=1000{print $1}' /etc/passwd`, `awk '{s+=$1} END{print s}'` sum.
- `find . -name '*.log' -mtime +7 -delete`; `find / -type f -size +100M 2>/dev/null`; `find . -type f -print0 | xargs -0 grep foo`. `xargs -P4 -n1` parallel; `-I{}` placeholder. `cut -d, -f2`, `tr`, `column -t`, `jq` (JSON).
- Pipes/redir: `>` overwrite, `>>` append, `2>&1` stderr→stdout (order matters: `>f 2>&1`), `&>f` both, `<` stdin, `<<<` here-string, `2>/dev/null` drop errors. FDs: `0` stdin, `1` stdout, `2` stderr. `tee f` splits to file+stdout. `cmd1 | cmd2`: pipe exit status is last cmd unless `set -o pipefail`.

## Disk, Inodes, Memory, FDs
- `df -h` (space), `df -i` (**inodes** — can exhaust while bytes free → "No space left"), `du -sh *`, `du -h --max-depth=1 | sort -h`. `lsblk`, `blkid`, `mount`, `/etc/fstab`. `ncdu` interactive.
- Deleted-but-open file still eats space until process closes: `lsof +L1` or `lsof | grep deleted`; fix = restart holder or truncate via `/proc/PID/fd/N`.
- `free -h`: "available" is what matters, not "free" (cache is reclaimable). `lsof -i :8080` (who holds port), `lsof -p PID`, `lsof -u user`. FD limit per proc: `ulimit -n`.

## Users, Groups, Cron, Limits
- `id`, `whoami`, `groups`, `/etc/passwd`, `/etc/group`, `/etc/shadow`. `useradd -m -s /bin/bash u`, `usermod -aG docker u` (`-a` = append, forgetting it wipes other groups), `passwd u`. Group change needs re-login or `newgrp`.
- Cron: `crontab -e`, fields `min hr dom mon dow cmd`; `*/5 * * * *` every 5 min; logs to mail/`/var/log/syslog`. Cron has minimal `$PATH`/env — use absolute paths. systemd-timer alt: `OnCalendar=daily`, `OnUnitActiveSec=1h`, `Persistent=true` (catch missed runs).
- `ulimit -a`; `-n` open files, `-u` procs, `-c` core size. Persist: `/etc/security/limits.conf` or systemd `LimitNOFILE=`. cgroups (v2 `/sys/fs/cgroup`) cap CPU/mem/IO per unit: `MemoryMax=`, `CPUQuota=`.

## Packages, Debug, Env, Net
- Debian: `apt update && apt install pkg`, `apt-cache search`, `dpkg -l`, `dpkg -S /path` (which pkg owns file). RHEL: `dnf install`, `rpm -qa`, `rpm -qf /path`.
- `strace -f -e trace=open,read -p PID` (syscalls — find missing files/EACCES); `ltrace` (lib calls). `lsof`, `dmesg -T` (kernel/OOM), `/proc/PID/{status,limits,environ,fd,cwd}`.
- Env: `export VAR=val`, `env`, `printenv VAR`, `unset VAR`. Persist login: `~/.bashrc` (interactive) / `~/.profile` (login). `PATH=$PATH:/new/bin` (never clobber). Per-cmd: `VAR=x cmd`.
- Net: `ip a` (addrs), `ip r` (routes), `ss -tlnp` (listening TCP+PID; replaces netstat), `ss -s` summary, `curl -v`, `dig`, `nc -zv host 443`, `ping`, `traceroute`, `mtr`.
- Archives: `tar -czf a.tgz dir/`, `tar -xzf a.tgz`, `tar -tzf` list, `-C /dest` extract dir. `scp f user@host:/path`, `rsync -avz --delete src/ host:/dst/`.

## Gotchas → Fix
- **Permission denied** on exec → `chmod +x f`; on file → wrong owner (`chown`) or missing dir `x`; try `sudo`. On a script → check shebang `#!/usr/bin/env bash`.
- **Disk full but files deleted** → open FD holding it; `lsof | grep deleted`, restart holder. **"No space" with free `df -h`** → inodes full (`df -i`), delete many small files.
- **Zombie `<defunct>`** → parent didn't `wait()`; harmless (just a PID slot) but kill/restart the *parent*, not the zombie (`kill -9` can't reap it). **Orphan** → reparented to PID 1, fine.
- **command not found** → not installed or not on `$PATH`; new `$PATH` not seen → re-`source` rc or new shell. **Sudo drops env** → use `sudo -E` or `sudo env VAR=x cmd`.
- **`rm -rf` irreversible**, no trash; never `rm -rf "$X/"` if `$X` may be empty/unset — `set -u` guards. Quote all expansions: `"$var"`, `"$@"` — spaces/globs break unquoted.
- **`Too many open files`** → raise `ulimit -n` + `LimitNOFILE=`; often an FD leak (`lsof -p PID | wc -l`).
- **CRLF `^M` breaks scripts** (`bad interpreter`) → `dos2unix f` or `sed -i 's/\r$//' f`.
- **`kill` won't stop process** → likely `D` state (uninterruptible I/O), wait or reboot; or it re-spawns (systemd `Restart=`, stop the unit).
- **Editing root file "read-only"** → `sudo`; in vim `:w !sudo tee %`.
- **`[ ]` tests**: strings `=`/`!=`, numbers `-eq`/`-lt`/`-gt`; always quote `[ "$a" = b ]` (empty var → syntax error). Prefer `[[ ]]` in bash.
- **OOM-killed process vanishes silently** → check `dmesg -T | grep -i oom` / `journalctl -k`.
