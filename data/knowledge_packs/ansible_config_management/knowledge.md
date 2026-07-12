# Ansible Config Management

## Model
- **Agentless, push-based**: control node connects over SSH (WinRM for Windows) and runs tasks; no daemon on targets, only Python + SSH required. Local execution via `connection: local`.
- **Idempotent** by design: modules describe *desired state*; a converged host reports `ok` (no change), otherwise `changed`. Re-running should be a no-op — this is the core contract.
- Execution: control node ships module code to the target, runs it, collects JSON result. `ansible` (ad-hoc), `ansible-playbook` (playbooks), `ansible-inventory`, `ansible-vault`, `ansible-galaxy`.
- Ad-hoc: `ansible web -m ping`, `ansible all -m ansible.builtin.apt -a "name=nginx state=present" --become`.

## Inventory
- Static INI/YAML: groups of hosts; `[web]`, `[db]`, group-of-groups `[prod:children]`. Vars: `[web:vars]` or `host_vars/`, `group_vars/`.
```yaml
all:
  children:
    web: { hosts: { web1.example.com: {}, web2.example.com: {} } }
```
- **Dynamic inventory**: plugins (`aws_ec2`, `gcp_compute`, `azure_rm`) query cloud APIs live; `ansible-inventory --graph -i inv.aws_ec2.yml`. `constructed`/`group_by` build groups from facts/tags.
- `ansible_host`, `ansible_user`, `ansible_port`, `ansible_python_interpreter` set connection per host.

## Playbooks
- A playbook = ordered list of **plays**; a play maps `hosts:` to `tasks:`, run top-to-bottom, one task fully across all hosts before the next (linear strategy).
```yaml
- name: web tier
  hosts: web
  become: true
  vars: { pkg: nginx }
  tasks:
    - name: install
      ansible.builtin.apt: { name: "{{ pkg }}", state: present }
      notify: restart nginx
  handlers:
    - name: restart nginx
      ansible.builtin.service: { name: nginx, state: restarted }
```
- **Handlers**: triggered by `notify` **only when the task reports `changed`**; run **once, at end of play** (after all tasks), in the order they are *defined* (not notified). `meta: flush_handlers` forces them mid-play.
- Always name tasks (readable output, `--start-at-task`). Prefer fully-qualified collection names (FQCN) `ansible.builtin.copy`.

## Modules
- Idempotent modules >> `command`/`shell`. Common: `apt`/`yum`/`dnf`/`package`, `service`/`systemd`, `copy`, `template`, `file`, `lineinfile`, `blockinfile`, `user`, `git`, `uri`, `get_url`, `unarchive`, `stat`, `command`, `shell`.
- `command` (no shell, safe) vs `shell` (pipes/redirects/globs, needs quoting). Both are **not idempotent** — always report `changed` unless guarded.

## Variables
- **Precedence** (low->high, abbreviated): role defaults (`defaults/main.yml`) < inventory group_vars/all < inventory host_vars < playbook `vars` < `vars_files`/`vars_prompt` < role `vars/main.yml` < block/task `vars` < `set_fact`/registered < `-e`/`--extra-vars` (**always wins**).
- **Facts**: gathered by `setup` at play start (`ansible_facts.*`, `ansible_distribution`, `ansible_default_ipv4.address`). Disable with `gather_facts: false` for speed. Custom facts in `/etc/ansible/facts.d/*.fact`.
- `register:` captures task result -> reuse (`result.stdout`, `result.rc`, `result.changed`). `set_fact` sets a runtime var.
- Magic vars: `hostvars[...]`, `groups['web']`, `inventory_hostname`, `ansible_play_hosts`.

## Templates (Jinja2)
- `template:` renders `.j2` with all vars/facts -> file. `{{ var }}`, `{% for %}`, `{% if %}`, filters `| default('x')`, `| mandatory`, `| to_nice_yaml`, `| b64encode`, `| ipaddr`. `{{ var | default(omit) }}` drops an arg entirely.
- `lineinfile`/`blockinfile` for surgical edits; `template` for whole managed files (add an `# ANSIBLE MANAGED` header).

## Roles & Galaxy
- Role structure: `tasks/`, `handlers/`, `templates/`, `files/`, `vars/`, `defaults/`, `meta/` (deps), `library/`. `roles/` beside the playbook auto-discovered.
- `ansible-galaxy install -r requirements.yml` (roles + collections); collections are the modern distribution unit (`ansible-galaxy collection install community.general`). Use `defaults/` for user-overridable, `vars/` for internal constants.

## Loops, conditionals, idempotency controls
- `loop: [a, b]` with `item`; `loop: "{{ mylist }}"`; `loop_control: { label: "{{ item.name }}", loop_var: pkg }`. (`with_items` is legacy.)
- `when: ansible_os_family == "Debian"`; `when: result.rc != 0`. Conditions on a loop evaluate per item.
- **Force idempotency on command/shell**:
  - `creates: /path` / `removes: /path` — skip if file exists/absent.
  - `changed_when: "'updated' in result.stdout"` / `changed_when: false` — override reported change.
  - `failed_when: result.rc not in [0, 2]` — custom failure.
  - `--check` (dry run) + `--diff`; `check_mode: false` to always run a read-only probe.

## Vault, tags, errors
- `ansible-vault encrypt group_vars/prod/vault.yml`; `--ask-vault-pass` or `--vault-password-file`. `!vault` inline for single values. Convention: put secrets in `vault_*` vars, reference from plaintext vars.
- `--tags deploy`, `--skip-tags slow`; `tags: [always]` always run, `tags: [never]` only when named.
- Error handling: `ignore_errors: true`; `block:`/`rescue:`/`always:` (try/catch/finally); `any_errors_fatal: true` aborts all hosts on first failure; `max_fail_percentage`.
- `serial: 2` / `serial: "25%"` rolling batches; `throttle`; `run_once: true`; `delegate_to: localhost` (run task elsewhere, e.g. load-balancer drain).
- `strategy: free` lets hosts race ahead independently; default `linear` locksteps.

## Collections, plugins, config
- Collections bundle modules/roles/plugins under a namespace (`community.general`, `ansible.posix`, `amazon.aws`); pin in `requirements.yml` + `ansible-galaxy collection install -r`. `collections:` key in a play sets search path.
- Plugin types: connection, lookup (`{{ lookup('env','HOME') }}`, `file`, `password`, `hashi_vault`), filter, callback (output formatting), inventory, strategy.
- `ansible.cfg` (cwd > `~/.ansible.cfg` > `/etc/ansible/`): `forks` (parallelism, default 5), `host_key_checking`, `pipelining = True` (big speedup, needs `requiretty` off in sudoers), `roles_path`, `retry_files_enabled`. Env override `ANSIBLE_*`.
- `--forks 50` widens fan-out; `-C`/`--check` dry run; `-D`/`--diff` show changes; `-v`/`-vvv` verbosity; `--limit web1` scopes hosts; `--list-tasks`/`--list-hosts` preview.

## Performance & execution
- `become: true` privilege escalation (default `sudo`); `become_user`, `become_method: sudo|su|doas`. Set at play/task; `-K` prompts for become password.
- Speed: enable `pipelining`, raise `forks`, use `gather_facts: false` or `gather_subset: '!all,min'` when facts unused, `async:`/`poll:` for long tasks (fire-and-forget), `mitogen` strategy plugin, SSH `ControlPersist` (default on).
- `import_*` (static, parsed at parse time — tags/handlers propagate) vs `include_*` (dynamic, evaluated at runtime — needed for loops/conditionals over whole files, but `--list-tasks` can't see inside).
- `ansible-lint` catches non-idempotent patterns, deprecated syntax, missing FQCN; `molecule` tests roles against containers/VMs.

## Gotchas -> Fix
- **`command`/`shell` always `changed`** -> add `creates:`/`removes:`, or `changed_when:` / `changed_when: false`; better, replace with a real module.
- **Handler never fires** -> the notifying task reported `ok` (already converged) or the play errored before end -> confirm the task actually `changed`; `meta: flush_handlers` to run before an abort; on failure handlers are skipped unless `force_handlers: true`.
- **`-e` var can't be overridden** -> extra-vars have the highest precedence by design; don't use them for defaults — use `group_vars`/role `defaults`.
- **Variable precedence surprise** -> role `vars/main.yml` beats inventory group_vars; move overridable values to `defaults/main.yml` (lowest role precedence). `ansible-inventory --host h` to inspect resolved vars.
- **Stale facts / fact caching wrong** -> `gather_facts: false` then referencing `ansible_*` fails; run `setup` or enable a fact cache (`fact_caching = jsonfile/redis`) and remember cached facts can be outdated -> `--flush-cache`.
- **Rolling deploy takes all hosts down** -> no `serial:` -> add `serial:` + `max_fail_percentage`, and `delegate_to` LB to drain/re-add around the batch.
- **No `--check` support** -> some modules (esp `command`/`shell`) don't honor check mode -> add `check_mode: false` on read-only probes, guard writes with `when`.
- **Jinja templating a bare `{{ }}` at line start in YAML** -> parser error -> quote the whole value: `key: "{{ var }}"`.
- **Unreachable != failed** -> SSH/host down is `unreachable`, not caught by `rescue`/`ignore_errors` -> use `ignore_unreachable: true`.
- **`with_items` + `apt`/`yum` slow** (loop installs one-by-one) -> pass the list directly: `apt: name="{{ pkgs }}"` (package modules take a list, one transaction).
- **`lineinfile` matching multiple lines** -> only edits last match; ambiguous regexp corrupts files -> anchor regexp, prefer `template` for whole files.
- **Secrets leak in output/`--diff`** -> mark `no_log: true` on tasks handling secrets; vault-encrypt at rest.
- **Non-deterministic dict ordering / undefined var** -> enable strict: `-e ANSIBLE_JINJA2_NATIVE=1` for types; set `mandatory`/`default` filters to fail loudly instead of rendering empty.
- **`become` needs a password but pipelining/tty conflicts** -> `sudo: requiretty` breaks pipelining -> remove `requiretty` in sudoers, or disable pipelining; pass `-K` for become password.
- **Handlers lost across `include_tasks`** -> dynamic includes don't propagate handler notifications the same as `import_tasks` -> use `import_tasks` when you need static handler/tag inheritance.
- **Idempotence not tested** -> a role silently reports `changed` every run -> add a Molecule `idempotence` scenario (second converge must report 0 changed) and `ansible-lint` in CI.
- **`gather_facts` slow at scale** -> full fact gathering on hundreds of hosts adds minutes -> `gather_subset: '!all,!min,network'` or a fact cache; gather once and reuse via `delegate_facts`.
- **Wrong Python interpreter on target** -> module fails or uses system Python 2 -> set `ansible_python_interpreter: /usr/bin/python3` (or `auto_silent`) in inventory/group_vars.
