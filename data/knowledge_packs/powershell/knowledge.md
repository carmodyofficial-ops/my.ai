# PowerShell

## Core model: objects, not text
- The pipeline passes **.NET objects**, not strings (vs bash). `Get-Process | Sort-Object CPU | Select-Object -First 5 Name,CPU` — properties survive the pipe; no `awk`/`cut` parsing.
- Cmdlets are **Verb-Noun**: `Get-*`, `Set-*`, `New-*`, `Remove-*`, `Start-*`. `Get-Command`, `Get-Help <cmd> -Full -Examples`, `Get-Member` (inspect an object's properties/methods — your main discovery tool).
- Everything returns objects to the pipeline; anything not captured/assigned goes to output. `Get-Member` on any pipeline: `... | Get-Member`.
- PowerShell (Core) `pwsh` = cross-platform 7+; Windows PowerShell 5.1 = Windows-only legacy. Prefer 7+.

## Pipeline & $_
- `$_` (or `$PSItem`) = current pipeline object inside script blocks.
- `Where-Object { $_.Status -eq 'Running' }` filters; `ForEach-Object { $_.Name }` transforms/acts per item.
- Simplified syntax (PS3+): `Where-Object Status -eq Running`, `ForEach-Object Name`.
- `Select-Object` picks/computes properties: `Select-Object Name,@{n='GB';e={$_.Length/1GB}}` (calculated property `n`/`e`), `-First/-Last/-Unique/-ExpandProperty`.
- `-ExpandProperty` unwraps one property to raw values (vs a wrapper object) — key for feeding a plain list downstream.
- Order that scales: **filter left** (`Where-Object` early, or provider `-Filter`), select/format right.

## Variables, types, operators
- `$x = 5`; `[int]$n = '42'` (cast). `$null`, `$true`, `$false`. Automatic: `$_`, `$args`, `$PSItem`, `$PSCmdlet`, `$Error`, `$?` (last success), `$LASTEXITCODE` (native exe).
- Arithmetic `+ - * / %`; assignment `+= -=`; size suffixes `1KB 1MB 1GB 1TB`.
- **Comparison operators are words** (not `<`/`>`, which are redirection): `-eq -ne -lt -le -gt -ge`. String/pattern: `-like` (wildcards `*?`), `-match` (regex, sets `$Matches`), `-replace` (regex), `-contains`/`-in` (collection membership), `-notmatch` etc. Case-sensitive variants prefix `c` (`-ceq`, `-cmatch`).
- On an array, a comparison **filters**: `$nums -gt 5` returns matching elements.
- Logical `-and -or -not`/`!`. Boolean context: empty string, `0`, `$null`, empty array are falsy.
- Ranges `1..10`; array `$a = 1,2,3` or `@(...)`; index `$a[0]`, `$a[-1]`, `$a[1..3]`.

## Hashtables, PSCustomObject, splatting
- Hashtable: `$h = @{ Name='Ann'; Age=30 }`; access `$h.Name` / `$h['Name']`; add `$h.City='NYC'`. Ordered: `[ordered]@{...}`.
- **PSCustomObject** (structured record): `[pscustomobject]@{ Name='Ann'; Age=30 }` — keeps key order, ideal for output rows and `Export-Csv`.
- **Splatting** = pass a param hashtable with `@`: `$p = @{Path='C:\'; Recurse=$true}; Get-ChildItem @p`. Cleans up long calls; `@p` (splat) not `$p`.

## Filtering / selecting / iterating recap
- `Where-Object` filter | `Select-Object` shape/limit | `ForEach-Object` per-item action | `Sort-Object -Property x -Descending` | `Group-Object x` | `Measure-Object -Sum -Average` | `Sort ... -Unique`.

## Providers
- Uniform path model: `Get-ChildItem`, `Get-Item`, `Set-Location` work across drives/providers.
- FileSystem: `Get-ChildItem -Path C:\logs -Recurse -Filter *.log`, `Get-Content`, `Set-Content`, `Test-Path`, `Copy-Item`, `Remove-Item`.
- Registry (Windows): `Get-ItemProperty 'HKLM:\SOFTWARE\...'`, `Set-ItemProperty`, `New-Item`.
- Env vars via provider: `$env:PATH`, `Get-ChildItem Env:`. Others: `Cert:`, `Function:`, `Variable:`, `Alias:`.

## Error handling
- **Non-terminating** errors (default) don't stop the pipeline — they go to `$Error` and the error stream. **Terminating** errors trigger `catch`.
- `try { ... } catch { $_.Exception.Message } finally { ... }`.
- Force a cmdlet's errors to terminate (so `catch` sees them): `-ErrorAction Stop`, or set `$ErrorActionPreference = 'Stop'` for the scope.
- `$ErrorActionPreference`: `Continue` (default), `Stop`, `SilentlyContinue` (suppress), `Ignore`.
- `throw 'msg'` raises a terminating error. `$Error[0]` = most recent. `$?` boolean of last op; `$LASTEXITCODE` for native executables (they don't throw).
- `-ErrorVariable ev`, `-WarningAction`, `Write-Error`, `Write-Warning`, `Write-Verbose` (gated by `-Verbose`/`$VerbosePreference`).

## Functions & advanced functions
```powershell
function Get-Big {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory, ValueFromPipeline)][string]$Path,
    [int]$MinMB = 10,
    [switch]$Recurse
  )
  process {                     # runs per pipeline item
    Get-ChildItem $Path -Recurse:$Recurse -File |
      Where-Object Length -gt ($MinMB * 1MB)
  }
}
```
- `[CmdletBinding()]` unlocks `-Verbose`, `-ErrorAction`, `-WhatIf`/`-Confirm` (with `SupportsShouldProcess`), common params.
- `param()` typed params; `[switch]` = boolean flag; `[Parameter(Mandatory)]`; default values; `[ValidateSet('A','B')]`, `[ValidateRange]`, `[ValidateNotNullOrEmpty]`.
- Pipeline input needs `ValueFromPipeline`/`ValueFromPipelineByPropertyName` + a `process {}` block; `begin{}`/`end{}` optional.
- `return` emits a value but **any uncaptured expression is also output** — a function returns everything written to the pipeline, not just `return`.

## Modules
- `Import-Module Name`, `Get-Module -ListAvailable`, `Install-Module Name -Scope CurrentUser` (PSGallery). A module = `.psm1` + `.psd1` manifest; `Export-ModuleMember` controls exposed functions.

## Scopes & operators extras
- Scopes: `Global`, `Script`, `Local`, `Private`; a function reads parent vars but writes create a local copy — use `$script:var` / `$global:var` to modify outer scope.
- Assignment shortcuts: `$a, $b = 1, 2` (multi-assign), `$a, $rest = 1,2,3` (`$rest` = remaining array).
- `-join` / `-split`: `'a','b' -join ',';  'a,b,c' -split ','`. `-f` format operator.
- Null-handling (PS7): `??` null-coalesce, `??=` assign-if-null, `?.`/`?[]` null-conditional. Ternary `cond ? a : b` (PS7).
- `&` call operator runs a command/path in a variable: `& $exe --flag`. `.` dot-sources into current scope.
- Pipeline chain operators (PS7): `&&` (run next on success), `||` (on failure).

## Data interchange
- JSON: `ConvertTo-Json -Depth 10`, `ConvertFrom-Json` (-> PSCustomObject). Watch default `-Depth 2` truncation.
- CSV: `Export-Csv -NoTypeInformation path.csv`, `Import-Csv` (-> objects with string properties). `ConvertTo-Csv`/`ConvertFrom-Csv` for in-memory.
- `Invoke-RestMethod` (auto-parses JSON to objects) vs `Invoke-WebRequest` (raw HTTP response).

## Remoting
- `Invoke-Command -ComputerName srv1,srv2 -ScriptBlock { Get-Service }` (runs in parallel, WinRM). `-Credential`.
- Persistent: `$s = New-PSSession -ComputerName srv1`; `Invoke-Command -Session $s {...}`; `Enter-PSSession $s`; `Remove-PSSession $s`.
- Cross-platform / cloud: SSH-based remoting (`-HostName ... -SSHTransport`). Remote objects are **deserialized snapshots** (methods stripped).

## Flow control & scripting
- `if/elseif/else`; `switch ($x) { 1 {...} 'a' {...} default {...} }` (supports `-Regex`, `-Wildcard`, arrays).
- Loops: `foreach ($i in $list) {...}` (collection iteration), `for`, `while`, `do..while`, `do..until`. `break`/`continue`.
- `1..5 | ForEach-Object { ... }` (pipeline) vs `foreach` statement (faster, whole collection in memory, no `$_`).
- Comments `#`, block `<# ... #>`; comment-based help (`.SYNOPSIS`, `.EXAMPLE`) above a function feeds `Get-Help`.
- Script params at top: `param([string]$Env='dev')` then run `.\deploy.ps1 -Env prod`.
- `$PSScriptRoot` = script's own dir; dot-source `. .\lib.ps1` to load functions into current scope.

## Useful cmdlets & patterns
- Objects: `New-Object`, `[pscustomobject]@{}`, `Add-Member`. `.NET` directly: `[System.Math]::Sqrt(2)`, `[datetime]::Now`, `[guid]::NewGuid()`.
- Output/streams: `Write-Output` (pipeline), `Write-Host` (console only, not pipeline), `Write-Verbose/-Debug/-Warning/-Error`, `Out-File`, `Out-GridView`, `Tee-Object`.
- Discovery: `Get-Command *service*`, `Get-Help`, `Get-Member`, `$obj | Format-List *`.
- Files/data: `Test-Path`, `Join-Path`, `Split-Path`, `Resolve-Path`, `Get-Content -Raw`, `Select-String` (grep-like, returns match objects).
- System: `Get-Process`, `Get-Service`, `Get-CimInstance` (modern WMI), `Start-Process`, `Stop-Process`.
- Compare/dedupe: `Compare-Object`, `Sort-Object -Unique`, `Group-Object`.
- Background/parallel: `Start-Job`/`Receive-Job`; `ForEach-Object -Parallel` (PS7); `Start-ThreadJob`.

## Strings & formatting
- `"Hello $name"` expands variables; `"$($obj.Prop)"` for sub-expressions. `'single quotes'` = literal, no expansion.
- Format operator: `"{0:N2} {1:P0}" -f 3.14159, 0.5`. Here-strings `@" ... "@` / `@' ... '@`.

## Pitfalls -> Fix
- **Pipeline outputs objects, expecting text** -> use `Get-Member`/`Select-Object`; parse with `.Property`, not string splitting.
- **`Format-*` ends the pipeline** -> `Format-Table/-List/-Wide` emit format objects for display only; never pipe them to `Export-Csv`/`Where-Object`/`ConvertTo-Json`. Do data work first, `Format-*` last.
- **Single item isn't an array** -> a command returning one object gives a scalar. Force array with `@(...)` or `[array]`; use `.Count` safely via `@($x).Count`.
- **`$null` comparison order** -> put `$null` on the **left**: `if ($null -eq $x)`. `if ($x -eq $null)` misbehaves when `$x` is an array (returns filtered elements, not a bool).
- **`-eq` vs `=`** -> `=` is assignment; comparisons use `-eq -lt` etc. `<`/`>` are redirection, not comparison.
- **Execution policy blocks scripts** (Windows) -> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`; or `pwsh -ExecutionPolicy Bypass -File x.ps1`. It's not a security boundary.
- **Function returns extra output** -> stray expressions/`Write-Output` all get returned; suppress with `$null = expr`, `| Out-Null`, or `[void](...)`.
- **String vs expandable string** -> variables only expand in `"double"` quotes; use `'single'` for literals (paths, regex, passwords).
- **Non-terminating errors ignored by try/catch** -> add `-ErrorAction Stop` or set `$ErrorActionPreference='Stop'`.
- **Native exe "success" not detected** -> external programs don't throw; check `$LASTEXITCODE`, not `$?` alone.
- **`ConvertTo-Json` truncates nesting** -> pass `-Depth 10+`.
- **Comparing case unexpectedly insensitive** -> `-eq`/`-match` are case-insensitive by default; use `-ceq`/`-cmatch` when case matters.
- **Splatting with `$` not `@`** -> invoke splat with `@hashName`; `$hashName` passes the hashtable as one argument.
- **Aliases in scripts** (`ls`, `%`, `?`, `gci`) -> use full cmdlet names for portability/readability; aliases differ across platforms.
- **Modifying a collection while iterating** -> build a new list or iterate a copy `@($items)`.
- **`Where`/`ForEach` method vs cmdlet** -> `.Where({})`/`.ForEach({})` are faster in-memory methods but load everything; pipeline cmdlets stream.
